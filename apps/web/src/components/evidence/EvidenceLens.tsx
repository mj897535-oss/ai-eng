"use client";

import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";

export interface AnnotationItem {
  annotation_id: string;
  start_char: number;
  end_char: number;
  start_time_ms: number | null;
  end_time_ms: number | null;
  candidate_error: string;
  suggested_correction: string;
  category_code: string;
  explanation: string;
  confidence: number;
  ai_status: string;
  flag: string;
  rubric_version?: string;
  prompt_version?: string;
  model_version?: string;
}

export interface EvidenceLensProps {
  assessmentId: string;
  assessmentType: string;
  transcript: string;
  wordCount: number;
  annotations: AnnotationItem[];
  bannerNotice: string;
  isVisibleToParticipant: boolean;
  rubricVersion: string;
  promptVersion?: string | null;
  modelVersion: string;
  audioPlaybackUrl?: string | null;
  isResearcher?: boolean;
  onReleaseResults?: () => Promise<void>;
}

// Category Badge Color Mappings
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; mark: string }> = {
  SVA: {
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-300 dark:border-emerald-800",
    mark: "bg-emerald-100 dark:bg-emerald-900/60 hover:bg-emerald-200 text-emerald-950 dark:text-emerald-100 border-b-2 border-emerald-500",
  },
  TNS: {
    bg: "bg-sky-50 dark:bg-sky-950/40",
    text: "text-sky-700 dark:text-sky-300",
    border: "border-sky-300 dark:border-sky-800",
    mark: "bg-sky-100 dark:bg-sky-900/60 hover:bg-sky-200 text-sky-950 dark:text-sky-100 border-b-2 border-sky-500",
  },
  WO: {
    bg: "bg-purple-50 dark:bg-purple-950/40",
    text: "text-purple-700 dark:text-purple-300",
    border: "border-purple-300 dark:border-purple-800",
    mark: "bg-purple-100 dark:bg-purple-900/60 hover:bg-purple-200 text-purple-950 dark:text-purple-100 border-b-2 border-purple-500",
  },
  AUX: {
    bg: "bg-amber-50 dark:bg-amber-950/40",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-300 dark:border-amber-800",
    mark: "bg-amber-100 dark:bg-amber-900/60 hover:bg-amber-200 text-amber-950 dark:text-amber-100 border-b-2 border-amber-500",
  },
  ART: {
    bg: "bg-teal-50 dark:bg-teal-950/40",
    text: "text-teal-700 dark:text-teal-300",
    border: "border-teal-300 dark:border-teal-800",
    mark: "bg-teal-100 dark:bg-teal-900/60 hover:bg-teal-200 text-teal-950 dark:text-teal-100 border-b-2 border-teal-500",
  },
  PREP: {
    bg: "bg-rose-50 dark:bg-rose-950/40",
    text: "text-rose-700 dark:text-rose-300",
    border: "border-rose-300 dark:border-rose-800",
    mark: "bg-rose-100 dark:bg-rose-900/60 hover:bg-rose-200 text-rose-950 dark:text-rose-100 border-b-2 border-rose-500",
  },
  PRO: {
    bg: "bg-indigo-50 dark:bg-indigo-950/40",
    text: "text-indigo-700 dark:text-indigo-300",
    border: "border-indigo-300 dark:border-indigo-800",
    mark: "bg-indigo-100 dark:bg-indigo-900/60 hover:bg-indigo-200 text-indigo-950 dark:text-indigo-100 border-b-2 border-indigo-500",
  },
  OTH: {
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-700 dark:text-slate-300",
    border: "border-slate-300 dark:border-slate-700",
    mark: "bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 text-slate-900 dark:text-slate-100 border-b-2 border-slate-500",
  },
};

const DEFAULT_COLOR = CATEGORY_COLORS["OTH"]!;

export function EvidenceLens({
  assessmentId,
  assessmentType,
  transcript,
  wordCount,
  annotations,
  bannerNotice,
  isVisibleToParticipant,
  rubricVersion,
  promptVersion,
  modelVersion,
  audioPlaybackUrl,
  isResearcher = false,
  onReleaseResults,
}: EvidenceLensProps) {
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(
    annotations.length > 0 && annotations[0] ? annotations[0].annotation_id : null
  );
  const [releasing, setReleasing] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Seek Audio Helper
  const handleSeekAudio = (timeSec: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, timeSec);
      audioRef.current.play().catch(() => {});
    }
  };

  const handleSpanClick = (ann: AnnotationItem) => {
    setSelectedAnnotationId(ann.annotation_id);
    if (ann.start_time_ms !== null) {
      handleSeekAudio(ann.start_time_ms / 1000);
    }
  };

  // Render Transcript with Highlighted Interactive Spans
  const renderInteractiveTranscript = () => {
    if (!transcript) return null;
    if (annotations.length === 0) {
      return <span>{transcript}</span>;
    }

    // Sort annotations by start_char
    const sorted = [...annotations].sort((a, b) => a.start_char - b.start_char);
    const elements: React.ReactNode[] = [];
    let currentIdx = 0;

    sorted.forEach((ann, i) => {
      // Non-error text preceding annotation
      if (ann.start_char > currentIdx) {
        elements.push(
          <span key={`text-${i}`}>
            {transcript.slice(currentIdx, ann.start_char)}
          </span>
        );
      }

      // Highlighted Span
      const isSelected = selectedAnnotationId === ann.annotation_id;
      const colorScheme = CATEGORY_COLORS[ann.category_code] ?? DEFAULT_COLOR;

      elements.push(
        <button
          key={`span-${ann.annotation_id}`}
          onClick={() => handleSpanClick(ann)}
          className={`inline-block px-1.5 py-0.5 mx-0.5 rounded transition-all cursor-pointer font-serif font-semibold text-left ${
            colorScheme.mark
          } ${
            isSelected
              ? "ring-2 ring-sky-500 ring-offset-1 dark:ring-offset-slate-900 shadow-sm"
              : ""
          }`}
          title={`Click to seek audio and view candidate card (${ann.category_code})`}
        >
          {transcript.slice(ann.start_char, ann.end_char)}
        </button>
      );

      currentIdx = ann.end_char;
    });

    // Remainder of transcript
    if (currentIdx < transcript.length) {
      elements.push(
        <span key="text-end">{transcript.slice(currentIdx)}</span>
      );
    }

    return elements;
  };

  const selectedAnnotation = annotations.find(
    (a) => a.annotation_id === selectedAnnotationId
  );

  return (
    <div className="space-y-6">
      {/* MANDATORY RESEARCH NOTICE BANNER */}
      <div className="p-3.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg flex items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-2 text-amber-900 dark:text-amber-200">
          <span className="font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
            Research Verification:
          </span>
          <span>{bannerNotice}</span>
        </div>

        {/* Release Button for Researchers */}
        {isResearcher && !isVisibleToParticipant && onReleaseResults && (
          <Button
            size="sm"
            variant="outline"
            className="text-xs shrink-0"
            onClick={async () => {
              setReleasing(true);
              try {
                await onReleaseResults();
              } finally {
                setReleasing(false);
              }
            }}
            disabled={releasing}
          >
            {releasing ? "Releasing..." : "Release to Participant"}
          </Button>
        )}
      </div>

      {/* EVIDENCE LENS MAIN CONTAINER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: INTERACTIVE TRANSCRIPT & AUDIO PLAYER (7 cols) */}
        <Card className="lg:col-span-7 p-6 space-y-6 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <span className="text-xs font-mono font-semibold text-sky-600 uppercase">
                Signature Feature A &bull; {assessmentType.replace("_", "-").toUpperCase()}
              </span>
              <h2 className="text-xl font-bold font-serif text-slate-900 dark:text-slate-50">Evidence Lens</h2>
            </div>
            <div className="flex items-center gap-2">
              <Chip variant="neutral" size="sm">{wordCount} Words</Chip>
              <Chip variant="primary" size="sm">{annotations.length} Candidate Deviations</Chip>
            </div>
          </div>

          {/* Audio Player with Seek Controller */}
          <div className="p-3.5 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
              <span>AUDIO PLAYBACK</span>
              <span>Click any highlighted word in the transcript below to seek audio</span>
            </div>
            {audioPlaybackUrl ? (
              <audio ref={audioRef} controls src={audioPlaybackUrl} className="w-full h-9" />
            ) : (
              <div className="text-xs text-slate-400 py-1 font-mono">
                Audio playback stream available in authenticated reviewer session.
              </div>
            )}
          </div>

          {/* Interactive Highlighted Transcript */}
          <div className="space-y-2">
            <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Faithful Spoken Transcript
            </div>
            <div className="p-5 bg-slate-50/50 dark:bg-slate-950/40 rounded-xl border border-slate-200 dark:border-slate-800 text-base leading-relaxed font-serif text-slate-900 dark:text-slate-100 selection:bg-sky-200">
              {renderInteractiveTranscript()}
            </div>
          </div>

          {/* Category Taxonomy Legend */}
          <div className="pt-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">
              Taxonomy Legend
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {Object.entries(CATEGORY_COLORS).map(([code, style]) => (
                <span
                  key={code}
                  className={`px-2 py-0.5 rounded border text-[11px] font-mono font-bold ${style.bg} ${style.text} ${style.border}`}
                >
                  {code}
                </span>
              ))}
            </div>
          </div>
        </Card>

        {/* RIGHT COLUMN: CANDIDATE ERROR CARD INSPECTOR (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-5 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-semibold">Candidate Deviation Card</h3>
              {selectedAnnotation && (
                <Chip variant="neutral" size="sm">
                  Confidence: {Math.round(selectedAnnotation.confidence * 100)}%
                </Chip>
              )}
            </div>

            {selectedAnnotation ? (
              <div className="space-y-4">
                {/* Category Badge & Flag */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-200 border border-sky-300 dark:border-sky-800">
                      {selectedAnnotation.category_code}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      Offsets: [{selectedAnnotation.start_char}:{selectedAnnotation.end_char}]
                    </span>
                  </div>

                  <Chip
                    variant={
                      selectedAnnotation.ai_status === "candidate"
                        ? "success"
                        : selectedAnnotation.flag === "acceptable_variation"
                        ? "primary"
                        : "warning"
                    }
                    size="sm"
                  >
                    {selectedAnnotation.ai_status}
                  </Chip>
                </div>

                {/* Candidate Error vs Proposed Correction */}
                <div className="p-3.5 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                    <span>CANDIDATE ERROR SPAN</span>
                    <span className="text-rose-600 font-semibold">Deviation</span>
                  </div>
                  <div className="text-base font-serif font-bold text-rose-600 line-through">
                    &ldquo;{selectedAnnotation.candidate_error}&rdquo;
                  </div>

                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-mono text-slate-500">
                    <span>PROPOSED CORRECTION</span>
                    <span className="text-emerald-600 font-semibold">Standard Form</span>
                  </div>
                  <div className="text-base font-serif font-bold text-emerald-600">
                    &ldquo;{selectedAnnotation.suggested_correction || "(Omit redundant token)"}&rdquo;
                  </div>
                </div>

                {/* Grammatical Rule Explanation */}
                <div className="space-y-1">
                  <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                    Rule Statement (Max 2 Sentences)
                  </div>
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed p-3 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 font-sans">
                    {selectedAnnotation.explanation}
                  </p>
                </div>

                {/* Acoustic Seek Trigger */}
                {selectedAnnotation.start_time_ms !== null && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full flex items-center justify-center gap-2 text-xs"
                    onClick={() => handleSeekAudio(selectedAnnotation.start_time_ms! / 1000)}
                  >
                    ▶ Listen to Spoken Evidence ({selectedAnnotation.start_time_ms / 1000}s)
                  </Button>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-400">
                No candidate error selected. Click any highlighted phrase in the Evidence Lens transcript.
              </div>
            )}
          </Card>

          {/* Research Provenance Card */}
          <Card className="p-4 bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500 space-y-1">
            <div className="font-bold text-slate-700 dark:text-slate-300">RESEARCH PROVENANCE</div>
            <div>Rubric Version: {rubricVersion}</div>
            <div>Prompt Version: {promptVersion || "v1.0-assessor"}</div>
            <div>Model Version: {modelVersion}</div>
            <div>Assessment ID: {assessmentId.slice(0, 8)}...</div>
          </Card>
        </div>
      </div>
    </div>
  );
}
