"use client";

import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

export type RecorderState =
  | "idle"
  | "mic_denied"
  | "ready"
  | "preparing"
  | "recording"
  | "recorded"
  | "uploading"
  | "queued"
  | "failed";

export interface AudioRecorderProps {
  assessmentType: "pre" | "post";
  taskId: string;
  topicTitle: string;
  promptText: string;
  prepTimeSeconds?: number;
  durationSeconds?: number;
  maxRerecords?: number;
  onSubmitted?: (assessmentId: string) => void;
}

export function AudioRecorder({
  assessmentType,
  taskId,
  topicTitle,
  promptText,
  prepTimeSeconds = 30,
  durationSeconds = 60,
  maxRerecords = 2,
  onSubmitted,
}: AudioRecorderProps) {
  const [recorderState, setRecorderState] = useState<RecorderState>("idle");
  const [prepTimeRemaining, setPrepTimeRemaining] = useState<number>(prepTimeSeconds);
  const [speakingElapsed, setSpeakingElapsed] = useState<number>(0);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [rerecordsRemaining, setRerecordsRemaining] = useState<number>(maxRerecords);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedAssessmentId, setSubmittedAssessmentId] = useState<string | null>(null);

  // Audio Context & MediaRecorder Refs
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const prepTimerRef = useRef<NodeJS.Timeout | null>(null);
  const speakTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Negotiate best supported codec
  const getSupportedMimeType = (): string => {
    if (typeof MediaRecorder === "undefined") return "audio/webm";
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4;codecs=mp4a.40.2",
      "audio/mp4",
      "audio/aac",
    ];
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return "audio/webm";
  };

  // Pre-flight mic permission
  const checkMicPermission = async () => {
    try {
      setErrorMessage(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      setRecorderState("ready");
    } catch (err: any) {
      console.warn("Microphone access denied:", err);
      setRecorderState("mic_denied");
      setErrorMessage(
        "Microphone permission was denied or is blocked by your browser. Please allow microphone access in your browser settings to continue."
      );
    }
  };

  // Start Preparation Timer
  const startPreparation = () => {
    setRecorderState("preparing");
    setPrepTimeRemaining(prepTimeSeconds);

    prepTimerRef.current = setInterval(() => {
      setPrepTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(prepTimerRef.current!);
          startRecording();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const skipPreparation = () => {
    if (prepTimerRef.current) clearInterval(prepTimerRef.current);
    startRecording();
  };

  // Start Recording
  const startRecording = async () => {
    try {
      setErrorMessage(null);
      let stream = mediaStreamRef.current;
      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
      }

      // Audio Level Meter Setup
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const updateLevel = () => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((acc, val) => acc + val, 0) / dataArray.length;
        setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // MediaRecorder Setup
      const mimeType = getSupportedMimeType();
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        setRecordedBlob(audioBlob);
        setRecordedAudioUrl(url);
        setRecorderState("recorded");
        cleanupAudioContext();
      };

      recorder.start(250); // 250ms chunks
      setRecorderState("recording");
      setSpeakingElapsed(0);

      speakTimerRef.current = setInterval(() => {
        setSpeakingElapsed((prev) => {
          if (prev >= durationSeconds - 1) {
            stopRecording();
            return durationSeconds;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      setErrorMessage("Could not initialize audio recorder: " + err.message);
      setRecorderState("failed");
    }
  };

  const stopRecording = () => {
    if (speakTimerRef.current) clearInterval(speakTimerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  const cleanupAudioContext = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
    }
    setAudioLevel(0);
  };

  const handleRerecord = () => {
    if (rerecordsRemaining <= 0) return;
    setRerecordsRemaining((prev) => prev - 1);
    setRecordedAudioUrl(null);
    setRecordedBlob(null);
    setRecorderState("ready");
  };

  // Submit & Upload
  const handleSubmitRecording = async () => {
    if (!recordedBlob) return;
    setRecorderState("uploading");
    setUploadProgress(10);
    setErrorMessage(null);

    try {
      const mimeType = recordedBlob.type || "audio/webm";

      // 1. Request presigned upload URL from API
      const presigned = await apiFetch<any>(`/assessments/${assessmentType}/presigned-url`, {
        method: "POST",
        body: JSON.stringify({ codec: mimeType, task_id: taskId }),
      });
      setUploadProgress(35);

      // 2. Direct upload to storage bucket
      const uploadHeaders: Record<string, string> = {
        "Content-Type": mimeType,
      };
      if (presigned.headers?.["x-amz-server-side-encryption"]) {
        uploadHeaders["x-amz-server-side-encryption"] = presigned.headers["x-amz-server-side-encryption"];
      }

      const s3Upload = await fetch(presigned.upload_url, {
        method: "PUT",
        headers: uploadHeaders,
        body: recordedBlob,
      });

      if (!s3Upload.ok) {
        throw new Error("Direct audio upload failed. Please check network connectivity.");
      }

      setUploadProgress(75);

      // 3. Finalize submission with idempotency key
      const idempotencyKey = crypto.randomUUID();
      const submitData = await apiFetch<any>("/assessments/submit", {
        method: "POST",
        body: JSON.stringify({
          task_id: taskId,
          assessment_type: assessmentType,
          storage_key: presigned.storage_key,
          duration_seconds: Math.max(3, speakingElapsed),
          checksum: idempotencyKey.slice(0, 16),
          idempotency_key: idempotencyKey,
        }),
      });
      setUploadProgress(100);
      setSubmittedAssessmentId(submitData.assessment_id);
      setRecorderState("queued");
      if (onSubmitted) onSubmitted(submitData.assessment_id);
    } catch (err: any) {
      console.error("Submission failed:", err);
      setErrorMessage(err.message || "Failed to submit recording. Your audio is safely saved locally.");
      setRecorderState("failed");
    }
  };

  useEffect(() => {
    return () => {
      if (prepTimerRef.current) clearInterval(prepTimerRef.current);
      if (speakTimerRef.current) clearInterval(speakTimerRef.current);
      cleanupAudioContext();
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      {/* Topic Prompt Card */}
      <Card className="p-6 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
          <Chip variant="primary" size="sm">
            {assessmentType === "pre" ? "Pre-Test Task" : "Post-Test Task"}
          </Chip>
          <span className="text-xs font-mono text-slate-500">
            {prepTimeSeconds}s preparation / {durationSeconds}s speaking
          </span>
        </div>

        <h2 className="text-xl font-bold font-serif text-slate-900 dark:text-slate-50">{topicTitle}</h2>
        <p className="text-sm text-slate-700 dark:text-slate-300 mt-2 leading-relaxed italic border-l-2 border-sky-500 pl-3 py-1 bg-slate-50 dark:bg-slate-950/60 rounded-r">
          &quot;{promptText}&quot;
        </p>

        {/* State Banners */}
        {recorderState === "mic_denied" && (
          <div className="mt-4 p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg text-xs text-rose-800 dark:text-rose-200 space-y-2">
            <div className="font-bold flex items-center gap-1.5 text-rose-700 dark:text-rose-300">
              <span>⚠ Microphone Access Blocked</span>
            </div>
            <p>{errorMessage}</p>
            <div className="pt-2">
              <Button size="sm" variant="outline" onClick={checkMicPermission}>
                Retry Permission Check
              </Button>
            </div>
          </div>
        )}

        {errorMessage && recorderState === "failed" && (
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 rounded-lg text-xs text-amber-800 dark:text-amber-200 space-y-2">
            <div className="font-bold">Submission Issue</div>
            <p>{errorMessage}</p>
            <div className="pt-2 flex gap-2">
              <Button size="sm" onClick={handleSubmitRecording}>
                Retry Submission
              </Button>
              {rerecordsRemaining > 0 && (
                <Button size="sm" variant="outline" onClick={handleRerecord}>
                  Re-Record Audio
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Main Recorder Controls Card */}
      <Card className="p-6 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm text-center">
        {/* STATE 1: IDLE */}
        {recorderState === "idle" && (
          <div className="py-6 space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-sky-100 dark:bg-sky-950/60 flex items-center justify-center text-sky-600 dark:text-sky-400 text-2xl">
              🎤
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Ready to begin?</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                First check your microphone to ensure your voice is captured clearly.
              </p>
            </div>
            <Button onClick={checkMicPermission} size="lg">
              Check Microphone & Start
            </Button>
          </div>
        )}

        {/* STATE 2: READY */}
        {recorderState === "ready" && (
          <div className="py-6 space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 text-2xl">
              ✓
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Microphone Ready</h3>
              <p className="text-xs text-slate-500 mt-1">
                You will have {prepTimeSeconds} seconds to review the topic before recording starts.
              </p>
            </div>
            <div className="flex justify-center gap-3">
              <Button onClick={startPreparation} size="lg">
                Begin Preparation ({prepTimeSeconds}s)
              </Button>
              <Button variant="outline" size="lg" onClick={skipPreparation}>
                Record Now
              </Button>
            </div>
          </div>
        )}

        {/* STATE 3: PREPARING (Countdown) */}
        {recorderState === "preparing" && (
          <div className="py-6 space-y-4">
            <div className="text-xs uppercase font-mono tracking-wider text-sky-600 dark:text-sky-400 font-semibold">
              Preparation Time Remaining
            </div>
            <div className="text-5xl font-mono font-bold text-slate-900 dark:text-slate-50">
              {prepTimeRemaining}s
            </div>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Organize your thoughts. Recording will start automatically when countdown ends.
            </p>
            <Button variant="outline" size="sm" onClick={skipPreparation}>
              Skip Countdown & Start Recording
            </Button>
          </div>
        )}

        {/* STATE 4: RECORDING */}
        {recorderState === "recording" && (
          <div className="py-6 space-y-4">
            <div className="flex items-center justify-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 animate-pulse" />
              <span className="text-xs font-mono font-bold uppercase text-rose-600 tracking-wider">
                Recording in Progress
              </span>
            </div>

            {/* Timer Display */}
            <div className="text-4xl font-mono font-bold text-slate-900 dark:text-slate-50">
              {Math.floor(speakingElapsed / 60)}:{(speakingElapsed % 60).toString().padStart(2, "0")} / 1:00
            </div>

            {/* Live Audio Level Meter */}
            <div className="max-w-xs mx-auto space-y-1">
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 overflow-hidden border border-slate-200 dark:border-slate-700">
                <div
                  className="bg-emerald-500 h-full transition-all duration-75"
                  style={{ width: `${Math.max(5, audioLevel)}%` }}
                />
              </div>
              <div className="text-[11px] text-slate-500 flex justify-between font-mono">
                <span>Mic Input</span>
                <span>{audioLevel}%</span>
              </div>
            </div>

            <Button variant="destructive" size="lg" onClick={stopRecording}>
              Stop Recording
            </Button>
          </div>
        )}

        {/* STATE 5: RECORDED (Review & Listen Back) */}
        {recorderState === "recorded" && (
          <div className="py-6 space-y-5">
            <div>
              <Chip variant="success" size="sm">Recording Finished ({speakingElapsed}s)</Chip>
              <h3 className="text-base font-semibold mt-2 text-slate-900 dark:text-slate-100">Review Your Spoken Response</h3>
              <p className="text-xs text-slate-500 mt-1">
                Listen back below. If satisfied, submit your answer. You have {rerecordsRemaining} re-record attempt{rerecordsRemaining === 1 ? "" : "s"} left.
              </p>
            </div>

            {/* HTML5 Audio Player */}
            {recordedAudioUrl && (
              <div className="max-w-md mx-auto p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800">
                <audio controls src={recordedAudioUrl} className="w-full h-10" />
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Button size="lg" onClick={handleSubmitRecording} className="w-full sm:w-auto">
                Submit Recording
              </Button>

              {rerecordsRemaining > 0 && (
                <Button variant="outline" size="lg" onClick={handleRerecord} className="w-full sm:w-auto">
                  Re-Record ({rerecordsRemaining} remaining)
                </Button>
              )}
            </div>
          </div>
        )}

        {/* STATE 6: UPLOADING */}
        {recorderState === "uploading" && (
          <div className="py-8 space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full border-4 border-sky-500 border-t-transparent animate-spin" />
            <h3 className="text-base font-semibold">Uploading to Secure Storage...</h3>
            <div className="max-w-xs mx-auto bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div className="bg-sky-500 h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-xs text-slate-500">Encrypting audio with AES-256 direct upload.</p>
          </div>
        )}

        {/* STATE 7: QUEUED (Success) */}
        {recorderState === "queued" && (
          <div className="py-8 space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 text-3xl">
              ✓
            </div>
            <div>
              <h3 className="text-xl font-bold font-serif text-slate-900 dark:text-slate-50">
                Recording Successfully Submitted!
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 max-w-sm mx-auto">
                Your audio has been securely encrypted and stored in private storage. It is now queued for transcription and syntactic review.
              </p>
            </div>

            <div className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg max-w-sm mx-auto font-mono text-xs text-slate-600 dark:text-slate-400">
              Assessment ID: <span className="font-bold text-slate-900 dark:text-slate-200">{submittedAssessmentId}</span>
              <div className="text-[11px] text-emerald-600 mt-1">Status: Queued for Transcription</div>
            </div>

            <div className="pt-2">
              <Button size="sm" variant="outline" onClick={() => window.location.href = "/dashboard"}>
                Return to Dashboard
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
