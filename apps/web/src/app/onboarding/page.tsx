"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ProgressSteps } from "@/components/ui/ProgressSteps";
import { Select } from "@/components/ui/Select";
import { apiFetch } from "@/lib/api";

interface ConsentData {
  version: string;
  effective_date: string;
  title: string;
  text: string;
  withdrawal_policy: string;
  already_consented: boolean;
  is_withdrawn: boolean;
}

interface OnboardingData {
  participant_id: string;
  research_code: string;
  onboarding_completed: boolean;
  current_step: string;
  is_withdrawn: boolean;
  consent_status: {
    agreed: boolean;
    version?: string | null;
  };
  profile: {
    age?: number | null;
    age_band?: string | null;
    mother_tongue?: string | null;
    school_medium?: string | null;
    country?: string | null;
    state?: string | null;
    city?: string | null;
  };
  config: {
    collect_name: boolean;
    age_collection_mode: "exact" | "band";
    collect_geography: boolean;
    current_consent_version: string;
  };
}

const ONBOARDING_STEPS = [
  { id: "consent", title: "Consent" },
  { id: "profile", title: "Profile" },
  { id: "mic_check", title: "Mic Check" },
  { id: "what_next", title: "Orientation" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [researchCode, setResearchCode] = useState<string>("SL-2026-XXXX");
  const [consentData, setConsentData] = useState<ConsentData | null>(null);
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Profile Form State
  const [ageBand, setAgeBand] = useState<string>("21-24");
  const [exactAge, setExactAge] = useState<string>("");
  const [motherTongue, setMotherTongue] = useState<string>("");
  const [schoolMedium, setSchoolMedium] = useState<string>("English");
  const [country, setCountry] = useState<string>("India");
  const [stateName, setStateName] = useState<string>("");
  const [cityName, setCityName] = useState<string>("");

  // Mic Check State
  const [micTested, setMicTested] = useState(false);
  const [isRecordingMic, setIsRecordingMic] = useState(false);
  const [micAudioLevel, setMicAudioLevel] = useState<number>(0);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        // 1. Fetch current consent document
        const cDoc = await apiFetch<ConsentData>("/consent/current");
        setConsentData(cDoc);

        // 2. Fetch onboarding state
        const state = await apiFetch<OnboardingData>("/onboarding/state");
        setResearchCode(state.research_code);

        if (state.onboarding_completed) {
          router.push("/");
          return;
        }

        if (state.current_step === "profile") {
          setCurrentStepIdx(1);
          setConsentAgreed(true);
        } else if (state.current_step === "mic_check") {
          setCurrentStepIdx(2);
          setConsentAgreed(true);
        } else if (state.current_step === "what_next") {
          setCurrentStepIdx(3);
          setConsentAgreed(true);
        } else {
          setCurrentStepIdx(0);
        }

        // Fill existing profile data if present
        if (state.profile) {
          if (state.profile.age_band) setAgeBand(state.profile.age_band);
          if (state.profile.age) setExactAge(String(state.profile.age));
          if (state.profile.mother_tongue) setMotherTongue(state.profile.mother_tongue);
          if (state.profile.school_medium) setSchoolMedium(state.profile.school_medium);
          if (state.profile.country) setCountry(state.profile.country);
          if (state.profile.state) setStateName(state.profile.state);
          if (state.profile.city) setCityName(state.profile.city);
        }
      } catch (err: unknown) {
        const error = err as { message?: string };
        setErrorMsg(error.message || "Failed to load onboarding status.");
      } finally {
        setLoading(false);
      }
    }
    loadData();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (audioContextRef.current) audioContextRef.current.close().catch(() => {});
    };
  }, [router]);

  // Step 1: Submit Consent Agreement
  const handleAgreeConsent = async () => {
    if (!consentAgreed) {
      setErrorMsg("Please read and tick the agreement checkbox before continuing.");
      return;
    }
    setErrorMsg(null);
    setSubmitting(true);
    try {
      await apiFetch("/consent/agree", {
        method: "POST",
        body: JSON.stringify({ consent_version: consentData?.version || "v1.0-jam-2026" }),
      });
      setCurrentStepIdx(1);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error.message || "Could not record consent.");
    } finally {
      setSubmitting(false);
    }
  };

  // Step 2: Submit Profile
  const handleSubmitProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!motherTongue.trim()) {
      setErrorMsg("Please enter your mother tongue / first language.");
      return;
    }
    setErrorMsg(null);
    setSubmitting(true);
    try {
      await apiFetch("/onboarding/profile", {
        method: "POST",
        body: JSON.stringify({
          age_band: ageBand,
          age: exactAge ? parseInt(exactAge, 10) : undefined,
          mother_tongue: motherTongue.trim(),
          school_medium: schoolMedium,
          country,
          state: stateName || undefined,
          city: cityName || undefined,
        }),
      });
      setCurrentStepIdx(2);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error.message || "Could not save profile.");
    } finally {
      setSubmitting(false);
    }
  };

  // Step 3: Mic Check
  const handleStartMicTest = async () => {
    setErrorMsg(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const audioUrl = URL.createObjectURL(audioBlob);
        setRecordedAudioUrl(audioUrl);
        setMicTested(true);
        setIsRecordingMic(false);
        stream.getTracks().forEach((t) => t.stop());
      };

      // Set up Web Audio Analyser for live level
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] ?? 0;
        const average = sum / dataArray.length;
        setMicAudioLevel(Math.min(100, Math.round((average / 128) * 100)));
        animFrameRef.current = requestAnimationFrame(updateVolume);
      };
      updateVolume();

      mediaRecorder.start();
      setIsRecordingMic(true);

      // Record for 4 seconds then stop
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop();
        }
      }, 4000);
    } catch (err: unknown) {
      setErrorMsg("Microphone access was denied or not found. Please enable microphone permissions in your browser.");
    }
  };

  const handleFinishMicCheck = async () => {
    setSubmitting(true);
    try {
      await apiFetch("/onboarding/complete-step", {
        method: "POST",
        body: JSON.stringify({ step: "mic_check" }),
      });
      setCurrentStepIdx(3);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error.message || "Failed to proceed.");
    } finally {
      setSubmitting(false);
    }
  };

  // Step 4: Finish Onboarding
  const handleFinishOnboarding = async () => {
    setSubmitting(true);
    try {
      await apiFetch("/onboarding/complete-step", {
        method: "POST",
        body: JSON.stringify({ step: "completed" }),
      });
      router.push("/assessment/pre");
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error.message || "Failed to complete onboarding.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center p-4 bg-background">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-accent border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm font-medium">Loading research protocol...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background text-foreground py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header with Pseudonymous Research Code */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-2">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Participant Onboarding
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
              Doctoral Research Study &bull; Department of Linguistics
            </p>
          </div>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20 self-start sm:self-auto">
            ID: {researchCode}
          </div>
        </div>

        {/* Progress Step Indicator */}
        <ProgressSteps steps={ONBOARDING_STEPS} currentStepIndex={currentStepIdx} />

        {errorMsg && (
          <div className="p-3.5 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm flex items-start gap-2.5">
            <span className="font-bold text-base leading-none">&times;</span>
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        {/* STEP 1: INFORMED CONSENT */}
        {currentStepIdx === 0 && (
          <Card className="p-5 sm:p-7 space-y-5 shadow-sm border border-border">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                  Step 1 of 4 &bull; Informed Consent
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  {consentData?.version || "v1.0-jam-2026"}
                </span>
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-foreground mt-1">
                {consentData?.title || "Research Participant Informed Consent"}
              </h2>
            </div>

            {/* Scrollable Consent Document Box */}
            <div className="h-64 sm:h-72 overflow-y-auto p-4 rounded-md bg-secondary/30 border border-border text-xs sm:text-sm text-muted-foreground space-y-3 leading-relaxed">
              <p className="font-medium text-foreground">
                Effective Date: {consentData?.effective_date || "January 15, 2026"}
              </p>
              <div className="whitespace-pre-line text-foreground/90 font-sans">
                {consentData?.text || "Study information loading..."}
              </div>
            </div>

            {/* Withdrawal Policy Callout Box */}
            <div className="p-3.5 rounded-lg bg-accent/5 border border-accent/20 text-xs sm:text-sm text-foreground space-y-1">
              <span className="font-semibold text-accent block">Voluntary Participation & Right to Withdraw</span>
              <p className="text-muted-foreground leading-normal">
                You may withdraw from this study at any time without penalty. All audio collection stops immediately upon withdrawal.
              </p>
            </div>

            {/* Agreement Checkbox */}
            <label className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-secondary/40 cursor-pointer transition-colors">
              <input
                type="checkbox"
                checked={consentAgreed}
                onChange={(e) => setConsentAgreed(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
              />
              <span className="text-xs sm:text-sm text-foreground">
                I have read and understood the study information. I voluntarily agree to participate under protocol <strong>{consentData?.version}</strong>.
              </span>
            </label>

            <Button
              className="w-full sm:w-auto"
              disabled={!consentAgreed || submitting}
              onClick={handleAgreeConsent}
            >
              {submitting ? "Recording Consent..." : "Agree & Continue to Profile"}
            </Button>
          </Card>
        )}

        {/* STEP 2: DEMOGRAPHIC PROFILE */}
        {currentStepIdx === 1 && (
          <Card className="p-5 sm:p-7 space-y-5 shadow-sm border border-border">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                Step 2 of 4 &bull; Demographic Background
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-foreground mt-1">
                Participant Language Profile
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                This context allows researchers to evaluate syntax patterns across linguistic backgrounds.
              </p>
            </div>

            <form onSubmit={handleSubmitProfile} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Age Band */}
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1.5">
                    Age Group
                  </label>
                  <Select
                    value={ageBand}
                    onChange={(e) => setAgeBand(e.target.value)}
                    options={[
                      { value: "18-20", label: "18 – 20 years" },
                      { value: "21-24", label: "21 – 24 years" },
                      { value: "25-29", label: "25 – 29 years" },
                      { value: "30+", label: "30+ years" },
                    ]}
                  />
                </div>

                {/* Medium of School Education */}
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1.5">
                    Medium of School Education
                  </label>
                  <Select
                    value={schoolMedium}
                    onChange={(e) => setSchoolMedium(e.target.value)}
                    options={[
                      { value: "English", label: "English Medium" },
                      { value: "Marathi", label: "Marathi Medium" },
                      { value: "Hindi", label: "Hindi Medium" },
                      { value: "Kannada", label: "Kannada Medium" },
                      { value: "Telugu", label: "Telugu Medium" },
                      { value: "Tamil", label: "Tamil Medium" },
                      { value: "Other", label: "Other / Vernacular" },
                    ]}
                  />
                </div>
              </div>

              {/* Mother Tongue Free Text */}
              <div>
                <label className="block text-xs font-medium text-foreground mb-1.5">
                  Mother Tongue / First Language <span className="text-danger">*</span>
                </label>
                <Input
                  placeholder="e.g. Marathi, Hindi, Telugu, Gujarati"
                  value={motherTongue}
                  onChange={(e) => setMotherTongue(e.target.value)}
                  required
                />
                <span className="text-[11px] text-muted-foreground mt-1 block">
                  Self-described; do not infer from your regional location.
                </span>
              </div>

              {/* Geographic Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Country</label>
                  <Input value={country} onChange={(e) => setCountry(e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">State / Province</label>
                  <Input
                    placeholder="e.g. Maharashtra"
                    value={stateName}
                    onChange={(e) => setStateName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">City</label>
                  <Input
                    placeholder="e.g. Pune"
                    value={cityName}
                    onChange={(e) => setCityName(e.target.value)}
                  />
                </div>
              </div>

              <div className="pt-2">
                <Button type="submit" className="w-full sm:w-auto" disabled={submitting}>
                  {submitting ? "Saving Profile..." : "Save Profile & Continue"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* STEP 3: MICROPHONE CHECK */}
        {currentStepIdx === 2 && (
          <Card className="p-5 sm:p-7 space-y-5 shadow-sm border border-border">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                Step 3 of 4 &bull; Audio Hardware Check
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-foreground mt-1">
                Test Your Microphone
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                Ensure your spoken speech is clearly captured before taking the speaking assessment.
              </p>
            </div>

            <div className="p-5 rounded-lg border border-border bg-secondary/20 text-center space-y-4">
              {!isRecordingMic && !micTested && (
                <div className="space-y-3">
                  <div className="w-12 h-12 rounded-full bg-accent/10 text-accent flex items-center justify-center mx-auto text-xl">
                    &#127897;
                  </div>
                  <p className="text-xs sm:text-sm text-muted-foreground max-w-sm mx-auto">
                    Click the button below and read: <br />
                    <em>&quot;Hello, I am testing my microphone for SyntaxLens.&quot;</em>
                  </p>
                  <Button onClick={handleStartMicTest}>
                    Start 4-Second Mic Check
                  </Button>
                </div>
              )}

              {isRecordingMic && (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2 text-danger font-semibold text-sm">
                    <span className="w-3 h-3 rounded-full bg-danger animate-pulse" />
                    Recording test sample (speaking now)...
                  </div>
                  {/* Audio Level Visualizer Meter */}
                  <div className="w-full max-w-xs mx-auto bg-border rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-accent h-full transition-all duration-75"
                      style={{ width: `${Math.max(5, micAudioLevel)}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground block font-mono">
                    Audio input level: {micAudioLevel}%
                  </span>
                </div>
              )}

              {micTested && !isRecordingMic && (
                <div className="space-y-4 text-left">
                  <div className="flex items-center gap-2.5 p-3 rounded-md bg-success/10 border border-success/30 text-success text-xs sm:text-sm font-medium">
                    <span className="text-base">&#10003;</span>
                    Microphone checked successfully. Audio signal captured.
                  </div>

                  {recordedAudioUrl && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-foreground block">
                        Listen to your test recording:
                      </label>
                      <audio controls src={recordedAudioUrl} className="w-full h-10" />
                    </div>
                  )}

                  <div className="flex flex-col sm:flex-row gap-2 pt-2">
                    <Button onClick={handleFinishMicCheck} disabled={submitting}>
                      {submitting ? "Saving..." : "Microphone Works &bull; Continue"}
                    </Button>
                    <Button variant="outline" onClick={handleStartMicTest}>
                      Re-Test Microphone
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* STEP 4: WHAT HAPPENS NEXT (ORIENTATION) */}
        {currentStepIdx === 3 && (
          <Card className="p-5 sm:p-7 space-y-6 shadow-sm border border-border">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                Step 4 of 4 &bull; Assessment Orientation
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-foreground mt-1">
                What Happens Next?
              </h2>
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                Plain-language overview of the upcoming spontaneous speaking assessment.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div className="p-4 rounded-lg bg-secondary/30 border border-border space-y-1.5">
                <span className="text-xs font-semibold text-accent block">1. Prompt & Preparation</span>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  You will see an everyday speaking topic (e.g. your daily routine). You have <strong>30 seconds</strong> of quiet prep time.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border space-y-1.5">
                <span className="text-xs font-semibold text-accent block">2. Speaking Response</span>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  You speak for about <strong>60 seconds</strong>. Speak naturally at your normal pace. Slips and pauses are completely normal.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border space-y-1.5">
                <span className="text-xs font-semibold text-accent block">3. Scientific Neutrality</span>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  During this assessment, no scores, hints or corrections are returned to keep the research data uninfluenced.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-secondary/30 border border-border space-y-1.5">
                <span className="text-xs font-semibold text-accent block">4. AI Tutor Sessions</span>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  After your pre-test, your personal AI tutor will be configured to help you practice specific syntax structures.
                </p>
              </div>
            </div>

            <div className="pt-2">
              <Button className="w-full sm:w-auto" onClick={handleFinishOnboarding} disabled={submitting}>
                {submitting ? "Completing Onboarding..." : "I'm Ready &bull; Start Speaking Pre-Test"}
              </Button>
            </div>
          </Card>
        )}
      </div>
    </main>
  );
}
