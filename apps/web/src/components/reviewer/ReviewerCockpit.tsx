"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/Dialog";
import { apiFetch } from "@/lib/api";

export interface CandidateAnnotation {
  annotation_id: string;
  start_char: number;
  end_char: number;
  start_time_ms: number | null;
  end_time_ms: number | null;
  span_text: string;
  category_code: string;
  suggested_correction: string;
  explanation: string;
  confidence: number;
  origin: string; // "ai" or "reviewer"
  review_status: string; // "unreviewed", "accepted", "rejected", "edited", "recategorized", "uncertain", "added"
  decision_id: string | null;
  reason: string | null;
  is_active_for_metrics: boolean;
  flag: string;
}

export interface ReviewerCockpitProps {
  assessmentId: string;
  participantCode: string;
  studyGroup: string;
  assessmentType: string;
  reviewStatus: string;
  isVerified: boolean;
  transcript: string;
  wordCount: number;
  audioUrl?: string | null;
  rubricVersion: string;
  modelVersion: string;
  annotations: CandidateAnnotation[];
  onDecisionRecorded?: (annotationId: string, decision: string) => void;
}

const CATEGORIES = ["TNS", "SVA", "WO", "AUX", "ART", "PREP", "PRO", "OTH"];

export function ReviewerCockpit({
  assessmentId,
  participantCode,
  studyGroup,
  assessmentType,
  reviewStatus: initialReviewStatus,
  isVerified: initialIsVerified,
  transcript,
  wordCount,
  audioUrl,
  rubricVersion,
  modelVersion,
  annotations: initialAnnotations,
}: ReviewerCockpitProps) {
  const [annotations, setAnnotations] = useState<CandidateAnnotation[]>(initialAnnotations);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [reviewStatus, setReviewStatus] = useState<string>(initialReviewStatus);
  const [isVerified, setIsVerified] = useState<boolean>(initialIsVerified);
  const [showShortcuts, setShowShortcuts] = useState<boolean>(false);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [lastActionNotice, setLastActionNotice] = useState<string | null>(null);

  // Edit Form State
  const [editSpan, setEditSpan] = useState<string>("");
  const [editCategory, setEditCategory] = useState<string>("");
  const [editCorrection, setEditCorrection] = useState<string>("");
  const [editExplanation, setEditExplanation] = useState<string>("");
  const [editReason, setEditReason] = useState<string>("");

  // Add Missed Annotation State
  const [addSpan, setAddSpan] = useState<string>("");
  const [addCategory, setAddCategory] = useState<string>("SVA");
  const [addCorrection, setAddCorrection] = useState<string>("");
  const [addExplanation, setAddExplanation] = useState<string>("");
  const [addReason, setAddReason] = useState<string>("");

  const audioRef = useRef<HTMLAudioElement | null>(null);

  const currentCandidate = annotations[currentIndex] || null;

  // Sync edit form with current candidate
  useEffect(() => {
    if (currentCandidate) {
      setEditSpan(currentCandidate.span_text);
      setEditCategory(currentCandidate.category_code);
      setEditCorrection(currentCandidate.suggested_correction);
      setEditExplanation(currentCandidate.explanation);
      setEditReason(currentCandidate.reason || "");
      setIsEditing(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, annotations]);

  // Audio Seek Helper
  const seekTo = useCallback((timeSec: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, timeSec);
      audioRef.current.play().catch(() => {});
    }
  }, []);

  // When candidate changes, seek audio if timestamp exists
  useEffect(() => {
    if (currentCandidate && currentCandidate.start_time_ms !== null) {
      seekTo(currentCandidate.start_time_ms / 1000);
    }
  }, [currentCandidate, seekTo]);

  // Autosave Decision Handler
  const handleRecordDecision = useCallback(
    async (
      decision: string,
      customFields?: {
        edited_span?: string;
        edited_category?: string;
        edited_correction?: string;
        edited_explanation?: string;
        reason?: string;
      }
    ) => {
      if (!currentCandidate) return;
      setSaving(true);
      setLastActionNotice(null);

      try {
        const payload = {
          annotation_id: currentCandidate.annotation_id,
          decision: decision,
          edited_span: customFields?.edited_span || undefined,
          edited_category: customFields?.edited_category || undefined,
          edited_correction: customFields?.edited_correction || undefined,
          edited_explanation: customFields?.edited_explanation || undefined,
          reason: customFields?.reason || `Keyboard decision: ${decision.toUpperCase()}`,
        };

        await apiFetch(`/reviews/cockpit/${assessmentId}/decisions`, {
          method: "POST",
          body: JSON.stringify(payload),
        });

        // Update local state derived view
        setAnnotations((prev) =>
          prev.map((ann, idx) => {
            if (idx === currentIndex) {
              return {
                ...ann,
                review_status: decision,
                category_code: customFields?.edited_category || ann.category_code,
                span_text: customFields?.edited_span || ann.span_text,
                suggested_correction: customFields?.edited_correction || ann.suggested_correction,
                explanation: customFields?.edited_explanation || ann.explanation,
                reason: customFields?.reason || ann.reason,
                is_active_for_metrics: decision !== "rejected",
              };
            }
            return ann;
          })
        );

        setLastActionNotice(`Candidate #${currentIndex + 1} marked as [${decision.toUpperCase()}]. Autosaved!`);
        setIsEditing(false);

        // Check if all resolved
        const remainingUnreviewed = annotations.filter(
          (a, i) => i !== currentIndex && a.review_status === "unreviewed"
        ).length;

        if (remainingUnreviewed === 0) {
          setReviewStatus("verified");
          setIsVerified(true);
        } else {
          setReviewStatus("partially_reviewed");
        }

        // Auto-advance to next candidate if available
        if (currentIndex < annotations.length - 1) {
          setCurrentIndex((prev) => prev + 1);
        }
      } catch (err: any) {
        alert("Failed to record decision: " + (err?.message || "Unknown error"));
      } finally {
        setSaving(false);
      }
    },
    [assessmentId, currentCandidate, currentIndex, annotations]
  );

  // Add Missed Annotation Handler
  const handleAddAnnotation = async () => {
    if (!addSpan || !addCorrection) {
      alert("Please provide the candidate span and proposed correction.");
      return;
    }
    setSaving(true);
    try {
      // Find character offsets in transcript if possible
      const startChar = transcript.indexOf(addSpan);
      const endChar = startChar >= 0 ? startChar + addSpan.length : 0;

      const payload = {
        span_text: addSpan,
        start_char: Math.max(0, startChar),
        end_char: Math.max(0, endChar),
        category_code: addCategory,
        suggested_correction: addCorrection,
        explanation: addExplanation || "Reviewer identified syntactic error missed by automated model.",
        reason: addReason || "Missed by AI.",
      };

      const res: any = await apiFetch(`/reviews/cockpit/${assessmentId}/annotations`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const newCandidate: CandidateAnnotation = {
        annotation_id: res.annotation_id,
        start_char: payload.start_char,
        end_char: payload.end_char,
        start_time_ms: null,
        end_time_ms: null,
        span_text: payload.span_text,
        category_code: payload.category_code,
        suggested_correction: payload.suggested_correction,
        explanation: payload.explanation,
        confidence: 1.0,
        origin: "reviewer",
        review_status: "added",
        decision_id: null,
        reason: payload.reason,
        is_active_for_metrics: true,
        flag: "none",
      };

      setAnnotations((prev) => [...prev, newCandidate]);
      setShowAddModal(false);
      setAddSpan("");
      setAddCorrection("");
      setAddExplanation("");
      setAddReason("");
      setCurrentIndex(annotations.length);
      setLastActionNotice("New reviewer-originated annotation added and logged!");
    } catch (err: any) {
      alert("Failed to add annotation: " + (err?.message || "Unknown error"));
    } finally {
      setSaving(false);
    }
  };

  // Global Keyboard Shortcuts (A, R, E, U, N, J, K, ?, etc.)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is actively typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") {
        return;
      }

      switch (e.key.toLowerCase()) {
        case "a":
          e.preventDefault();
          handleRecordDecision("accepted");
          break;
        case "r":
          e.preventDefault();
          handleRecordDecision("rejected");
          break;
        case "e":
          e.preventDefault();
          setIsEditing((prev) => !prev);
          break;
        case "u":
          e.preventDefault();
          handleRecordDecision("uncertain");
          break;
        case "n":
          e.preventDefault();
          setShowAddModal(true);
          break;
        case "j":
        case "arrowdown":
        case "]":
          e.preventDefault();
          if (currentIndex < annotations.length - 1) {
            setCurrentIndex((prev) => prev + 1);
          }
          break;
        case "k":
        case "arrowup":
        case "[":
          e.preventDefault();
          if (currentIndex > 0) {
            setCurrentIndex((prev) => prev - 1);
          }
          break;
        case "?":
          e.preventDefault();
          setShowShortcuts((prev) => !prev);
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleRecordDecision, currentIndex, annotations.length]);

  return (
    <div className="space-y-6">
      {/* TOP STATUS BAR & HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Link href="/admin/review-queue" className="hover:underline">Review Queue</Link>
            <span>/</span>
            <span className="font-mono text-slate-900 dark:text-slate-200 font-medium">{participantCode}</span>
            <span>/</span>
            <span className="font-mono text-xs capitalize">{assessmentType.replace("_", "-")} ({studyGroup})</span>
            <span>/</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-semibold">Reviewer Cockpit</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50 flex items-center gap-3">
            Reviewer Cockpit
            <span className="text-xs px-2.5 py-0.5 rounded font-mono font-semibold uppercase bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300">
              Signature Feature D
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
            Adjudicate automated candidate syntactic deviations. Append-only decisions, side-by-side evidence inspection, and full keyboard-only workflows.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Assessment Verification Badge */}
          <Chip variant={isVerified ? "success" : "warning"} size="sm">
            {isVerified ? "Assessment Verified" : `Status: ${reviewStatus.replace("_", " ").toUpperCase()} (FR-16)`}
          </Chip>
          <Chip variant="neutral" size="sm" className="hidden sm:inline-flex font-mono text-[11px]">
            Rubric: {rubricVersion}
          </Chip>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowShortcuts(true)}
            className="font-mono text-xs gap-1.5"
            title="Press ? for Keyboard Shortcuts"
          >
            <span className="px-1 py-0.2 bg-slate-200 dark:bg-slate-700 rounded text-[10px]">?</span> Shortcuts
          </Button>

          <Button
            size="sm"
            onClick={() => setShowAddModal(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs gap-1.5"
            title="Press N to add missed annotation"
          >
            <span className="px-1 py-0.2 bg-emerald-800 rounded text-[10px]">N</span> Add Missed Error
          </Button>
        </div>
      </div>

      {/* AUTOSAVE / ACTION FEEDBACK NOTIFICATION */}
      {lastActionNotice && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 rounded-lg text-xs font-mono text-emerald-800 dark:text-emerald-300 flex items-center justify-between animate-fade-in">
          <span>&bull; {lastActionNotice}</span>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-sans">Append-only audit row logged</span>
        </div>
      )}

      {/* AUDIO PLAYER & WAVEFORM INSPECTOR */}
      <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 space-y-3">
        <div className="flex items-center justify-between text-xs font-mono text-slate-500">
          <span className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            SYNCHRONIZED ACOUSTIC REPLAY
          </span>
          <span>
            {currentCandidate?.start_time_ms !== null && currentCandidate?.start_time_ms !== undefined
              ? `Focused on [${currentCandidate.span_text}] at ${(currentCandidate.start_time_ms / 1000).toFixed(1)}s`
              : "Audio timeline aligned with verbatim transcript"}
          </span>
        </div>

        {audioUrl ? (
          <audio ref={audioRef} controls src={audioUrl} className="w-full h-10" />
        ) : (
          <div className="h-10 bg-slate-100 dark:bg-slate-950 rounded flex items-center justify-center font-mono text-xs text-slate-400 border border-dashed border-slate-300 dark:border-slate-800">
            Audio stream available in authenticated reviewer session.
          </div>
        )}

        {/* TIMESTAMP-LINKED TRANSCRIPT WITH CONTEXT HIGHLIGHT */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800 font-serif text-base leading-relaxed text-slate-800 dark:text-slate-200">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-2">
            Faithful Verbatim Transcript ({wordCount} words):
          </span>
          {renderTranscriptWithContext(transcript, annotations, currentIndex, (idx) => setCurrentIndex(idx))}
        </div>
      </Card>

      {/* CANDIDATE NAVIGATION BAR */}
      <div className="flex items-center justify-between bg-slate-100 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-500 font-bold uppercase">
            Candidate Progress:
          </span>
          <span className="font-mono text-sm font-bold text-slate-900 dark:text-slate-100">
            {annotations.length > 0 ? `${currentIndex + 1} of ${annotations.length}` : "0 of 0"}
          </span>

          {currentCandidate && (
            <Chip
              variant={
                currentCandidate.origin === "reviewer"
                  ? "primary"
                  : currentCandidate.review_status === "accepted"
                  ? "success"
                  : currentCandidate.review_status === "rejected"
                  ? "danger"
                  : currentCandidate.review_status === "edited"
                  ? "warning"
                  : "neutral"
              }
              size="sm"
            >
              Origin: {currentCandidate.origin.toUpperCase()} &bull; Status: {currentCandidate.review_status.toUpperCase()}
            </Chip>
          )}
        </div>

        <div className="flex items-center gap-1.5 font-mono text-xs">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="text-xs py-1 px-2.5"
          >
            &larr; Prev [K]
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentIndex((prev) => Math.min(annotations.length - 1, prev + 1))}
            disabled={currentIndex >= annotations.length - 1}
            className="text-xs py-1 px-2.5"
          >
            Next [J] &rarr;
          </Button>
        </div>
      </div>

      {/* SIDE-BY-SIDE: AI SAID / REVIEWER SAYS PANEL */}
      {currentCandidate && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* LEFT: AI SAID PANEL */}
          <Card className="p-6 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <span className="text-xs font-mono uppercase tracking-wider text-sky-600 dark:text-sky-400 font-bold">
                AI Assessor Emitted
              </span>
              <span className="font-mono text-xs text-slate-400">
                Confidence: {(currentCandidate.confidence * 100).toFixed(0)}%
              </span>
            </div>

            <div>
              <span className="text-[11px] font-mono text-slate-400 uppercase">Target Span:</span>
              <div className="text-lg font-serif font-bold text-slate-900 dark:text-slate-100 p-2.5 bg-slate-50 dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800 mt-1">
                &ldquo;{currentCandidate.span_text}&rdquo;
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[11px] font-mono text-slate-400 uppercase">Category:</span>
                <div className="font-mono font-bold text-sm text-slate-800 dark:text-slate-200 mt-0.5">
                  <Chip variant="neutral" size="sm">{currentCandidate.category_code}</Chip>
                </div>
              </div>

              <div>
                <span className="text-[11px] font-mono text-slate-400 uppercase">Suggested Correction:</span>
                <div className="font-serif font-semibold text-sm text-emerald-700 dark:text-emerald-400 mt-0.5">
                  &ldquo;{currentCandidate.suggested_correction}&rdquo;
                </div>
              </div>
            </div>

            <div>
              <span className="text-[11px] font-mono text-slate-400 uppercase">Model Justification:</span>
              <p className="text-xs text-slate-600 dark:text-slate-300 font-serif leading-relaxed mt-1 p-3 bg-slate-50 dark:bg-slate-950/60 rounded border border-slate-200 dark:border-slate-800">
                {currentCandidate.explanation}
              </p>
            </div>

            <div className="text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
              Model: {modelVersion} &bull; Prompt: v1.0-assessor
            </div>
          </Card>

          {/* RIGHT: REVIEWER SAYS PANEL */}
          <Card className="p-6 bg-white dark:bg-slate-900 border-emerald-300 dark:border-emerald-800/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-700 dark:text-emerald-400 font-bold">
                Reviewer Adjudication
              </span>
              <Chip
                variant={
                  currentCandidate.review_status === "accepted"
                    ? "success"
                    : currentCandidate.review_status === "rejected"
                    ? "danger"
                    : currentCandidate.review_status === "edited"
                    ? "warning"
                    : "neutral"
                }
                size="sm"
              >
                {currentCandidate.review_status.toUpperCase()}
              </Chip>
            </div>

            {!isEditing ? (
              /* Reviewer Decision Actions */
              <div className="space-y-4">
                <div className="p-3 bg-slate-50 dark:bg-slate-950 rounded border border-slate-200 dark:border-slate-800 text-xs font-serif text-slate-700 dark:text-slate-300 space-y-1">
                  <div><strong>Effective Span:</strong> &ldquo;{currentCandidate.span_text}&rdquo;</div>
                  <div><strong>Effective Category:</strong> {currentCandidate.category_code}</div>
                  <div><strong>Effective Correction:</strong> &ldquo;{currentCandidate.suggested_correction}&rdquo;</div>
                  {currentCandidate.reason && <div><strong>Reviewer Note:</strong> {currentCandidate.reason}</div>}
                </div>

                {/* Primary Action Buttons */}
                <div className="grid grid-cols-2 gap-2.5">
                  <Button
                    onClick={() => handleRecordDecision("accepted")}
                    disabled={saving}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs gap-1.5"
                  >
                    <span className="px-1 py-0.2 bg-emerald-800 rounded text-[10px]">A</span> Accept Candidate
                  </Button>

                  <Button
                    onClick={() => handleRecordDecision("rejected")}
                    disabled={saving}
                    variant="outline"
                    className="border-rose-300 text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-mono text-xs gap-1.5"
                  >
                    <span className="px-1 py-0.2 bg-rose-200 dark:bg-rose-800 rounded text-[10px]">R</span> Reject (Not Error)
                  </Button>

                  <Button
                    onClick={() => setIsEditing(true)}
                    disabled={saving}
                    variant="outline"
                    className="font-mono text-xs gap-1.5"
                  >
                    <span className="px-1 py-0.2 bg-slate-200 dark:bg-slate-700 rounded text-[10px]">E</span> Edit / Recategorise
                  </Button>

                  <Button
                    onClick={() => handleRecordDecision("uncertain")}
                    disabled={saving}
                    variant="outline"
                    className="border-amber-300 text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/40 font-mono text-xs gap-1.5"
                  >
                    <span className="px-1 py-0.2 bg-amber-200 dark:bg-amber-800 rounded text-[10px]">U</span> Mark Uncertain
                  </Button>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] font-mono text-slate-500">
                  <span>Special Variations:</span>
                  <button
                    onClick={() =>
                      handleRecordDecision("acceptable_variation", {
                        reason: "Indian English acceptable regional variation.",
                      })
                    }
                    className="underline hover:text-emerald-600"
                  >
                    Indian English Variation
                  </button>
                  &bull;
                  <button
                    onClick={() =>
                      handleRecordDecision("transcription_related", {
                        reason: "Acoustic distortion or transcription artifact.",
                      })
                    }
                    className="underline hover:text-emerald-600"
                  >
                    Transcription-Related
                  </button>
                </div>
              </div>
            ) : (
              /* Inline Edit Form */
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <label className="block text-slate-500 mb-1">EDITED SPAN</label>
                  <input
                    type="text"
                    value={editSpan}
                    onChange={(e) => setEditSpan(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-500 mb-1">CATEGORY CODE</label>
                    <select
                      value={editCategory}
                      onChange={(e) => setEditCategory(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-500 mb-1">PROPOSED CORRECTION</label>
                    <input
                      type="text"
                      value={editCorrection}
                      onChange={(e) => setEditCorrection(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-500 mb-1">EXPLANATION</label>
                  <textarea
                    rows={2}
                    value={editExplanation}
                    onChange={(e) => setEditExplanation(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif text-xs"
                  />
                </div>

                <div>
                  <label className="block text-slate-500 mb-1">REASON FOR ADJUDICATION</label>
                  <input
                    type="text"
                    value={editReason}
                    onChange={(e) => setEditReason(e.target.value)}
                    placeholder="e.g. Adjusted boundaries to include auxiliary verb"
                    className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs"
                  />
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <Button
                    size="sm"
                    onClick={() =>
                      handleRecordDecision("edited", {
                        edited_span: editSpan,
                        edited_category: editCategory,
                        edited_correction: editCorrection,
                        edited_explanation: editExplanation,
                        reason: editReason || "Reviewer corrected candidate attributes.",
                      })
                    }
                    disabled={saving}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs"
                  >
                    Save Decision (Enter)
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsEditing(false)}
                    className="font-mono text-xs"
                  >
                    Cancel (Esc)
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* KEYBOARD SHORTCUTS CHEAT-SHEET MODAL */}
      <Dialog open={showShortcuts} onOpenChange={setShowShortcuts}>
        <DialogContent className="max-w-md bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
          <DialogHeader>
            <DialogTitle className="font-serif text-lg font-bold">Reviewer Keyboard Shortcuts</DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              High-throughput adjudication keybindings for the Reviewer Cockpit.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 font-mono text-xs py-2">
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Accept Candidate</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">A</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Reject Candidate (Not Error)</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">R</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Edit / Recategorise Inline</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">E</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Mark Uncertain / Dialect</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">U</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Add Missed Error (Reviewer-Originated)</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">N</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Next Candidate</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">J / &darr; / ]</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Previous Candidate</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">K / &uarr; / [</kbd>
            </div>
            <div className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-950 rounded">
              <span>Toggle Shortcuts Cheat-Sheet</span>
              <kbd className="px-2 py-0.5 bg-slate-200 dark:bg-slate-700 rounded font-bold">?</kbd>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ADD MISSED ERROR MODAL */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="max-w-md bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
          <DialogHeader>
            <DialogTitle className="font-serif text-lg font-bold">Add Missed Syntactic Deviation</DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Create a reviewer-originated candidate annotation clearly labelled in research provenance.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 font-mono text-xs py-2">
            <div>
              <label className="block text-slate-500 mb-1">DEVIANT SPAN IN TRANSCRIPT</label>
              <input
                type="text"
                value={addSpan}
                onChange={(e) => setAddSpan(e.target.value)}
                placeholder="e.g. by bus"
                className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-500 mb-1">CATEGORY CODE</label>
                <select
                  value={addCategory}
                  onChange={(e) => setAddCategory(e.target.value)}
                  className="w-full px-2 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-500 mb-1">SUGGESTED CORRECTION</label>
                <input
                  type="text"
                  value={addCorrection}
                  onChange={(e) => setAddCorrection(e.target.value)}
                  placeholder="e.g. on the bus"
                  className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-500 mb-1">EXPLANATION / JUSTIFICATION</label>
              <textarea
                rows={2}
                value={addExplanation}
                onChange={(e) => setAddExplanation(e.target.value)}
                placeholder="Describe why this constitutes a syntactic error per rubric..."
                className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 font-serif text-xs"
              />
            </div>

            <div>
              <label className="block text-slate-500 mb-1">NOTE / REASON</label>
              <input
                type="text"
                value={addReason}
                onChange={(e) => setAddReason(e.target.value)}
                placeholder="e.g. Preposition error overlooked by automated parser"
                className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <Button size="sm" variant="outline" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleAddAnnotation}
                disabled={saving}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs"
              >
                Save Reviewer Annotation
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Helper to render transcript highlighting current candidate with focus ring
function renderTranscriptWithContext(
  transcript: string,
  annotations: CandidateAnnotation[],
  currentIndex: number,
  onSelectIndex: (idx: number) => void
) {
  if (!transcript) return null;
  if (annotations.length === 0) return <span>{transcript}</span>;

  const sorted = [...annotations].map((ann, originalIdx) => ({
    ...ann,
    originalIdx,
  })).sort((a, b) => a.start_char - b.start_char);

  const elements: React.ReactNode[] = [];
  let currentPos = 0;

  sorted.forEach((ann, i) => {
    if (ann.start_char > currentPos) {
      elements.push(
        <span key={`txt-${i}`}>
          {transcript.slice(currentPos, ann.start_char)}
        </span>
      );
    }

    const isCurrent = ann.originalIdx === currentIndex;
    const isRejected = ann.review_status === "rejected";
    const isAccepted = ann.review_status === "accepted";
    const isEdited = ann.review_status === "edited";
    const isReviewerAdded = ann.origin === "reviewer";

    elements.push(
      <button
        key={`ann-${ann.annotation_id}`}
        onClick={() => onSelectIndex(ann.originalIdx)}
        className={`inline-block px-1.5 py-0.5 mx-0.5 rounded transition-all font-serif font-bold text-left cursor-pointer ${
          isRejected
            ? "line-through text-slate-400 bg-slate-200 dark:bg-slate-800"
            : isReviewerAdded
            ? "bg-purple-100 dark:bg-purple-900/60 text-purple-900 dark:text-purple-200 border-b-2 border-purple-500"
            : isAccepted
            ? "bg-emerald-100 dark:bg-emerald-900/60 text-emerald-950 dark:text-emerald-100 border-b-2 border-emerald-500"
            : isEdited
            ? "bg-amber-100 dark:bg-amber-900/60 text-amber-950 dark:text-amber-100 border-b-2 border-amber-500"
            : "bg-sky-100 dark:bg-sky-900/60 text-sky-950 dark:text-sky-100 border-b-2 border-sky-500"
        } ${
          isCurrent
            ? "ring-2 ring-emerald-500 ring-offset-2 dark:ring-offset-slate-900 scale-105 shadow-md"
            : "opacity-85 hover:opacity-100"
        }`}
        title={`[#${ann.originalIdx + 1}] ${ann.category_code} - Click to focus candidate`}
      >
        {transcript.slice(ann.start_char, ann.end_char) || ann.span_text}
      </button>
    );

    currentPos = Math.max(currentPos, ann.end_char);
  });

  if (currentPos < transcript.length) {
    elements.push(<span key="txt-end">{transcript.slice(currentPos)}</span>);
  }

  return elements;
}
