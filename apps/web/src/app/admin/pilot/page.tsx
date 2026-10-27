"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";

interface STTMetricItem {
  metric_id: string;
  assessment_id: string;
  provider: string;
  model_version: string;
  audio_duration_seconds: number;
  latency_ms: number;
  estimated_cost_usd: number;
  word_count: number;
  average_confidence: number;
  low_confidence_count: number;
  retry_count: number;
  created_at: string;
}

interface STTMetricsSummary {
  total_runs: number;
  total_audio_seconds: number;
  total_cost_usd: number;
  average_latency_ms: number;
  average_confidence: number;
  low_confidence_count: number;
  recent_jobs: STTMetricItem[];
}

interface TranscriptData {
  assessment_id: string;
  status: string;
  transcript: string | null;
  word_count: number;
  stt_confidence: number | null;
  low_confidence_flag: boolean;
  words: Array<{ word: string; start: number; end: number; confidence: number }>;
  revisions: Array<{
    revision_id: string;
    revised_transcript: string;
    revised_word_count: number;
    reason: string;
    diff_json: string | null;
    created_at: string;
  }>;
  retry_count: number;
  last_error: string | null;
}

export default function PilotTelemetryPage() {
  const [metrics, setMetrics] = useState<STTMetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string | null>(null);
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  // Revision modal state
  const [isRevisionOpen, setIsRevisionOpen] = useState(false);
  const [revisedText, setRevisedText] = useState("");
  const [revisionReason, setRevisionReason] = useState("");
  const [submittingRevision, setSubmittingRevision] = useState(false);

  useEffect(() => {
    fetchMetrics();
  }, []);

  async function fetchMetrics() {
    setLoading(true);
    try {
      const res = await apiFetch<STTMetricsSummary>("/assessments/metrics/stt");
      if (res) {
        setMetrics(res);
      }
    } catch (e) {
      console.error("Failed to load STT metrics", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadTranscriptDetails(assessmentId: string) {
    setSelectedAssessmentId(assessmentId);
    setLoadingTranscript(true);
    try {
      const res = await apiFetch<TranscriptData>(`/assessments/${assessmentId}/transcript`);
      if (res) {
        setTranscriptData(res);
        setRevisedText(res.transcript || "");
      }
    } catch (e) {
      console.error("Failed to load transcript", e);
    } finally {
      setLoadingTranscript(false);
    }
  }

  async function handleCreateRevision() {
    if (!selectedAssessmentId || !revisedText.trim() || !revisionReason.trim()) return;
    setSubmittingRevision(true);
    try {
      const res = await apiFetch(`/assessments/${selectedAssessmentId}/revisions`, {
        method: "POST",
        body: JSON.stringify({
          revised_transcript: revisedText.trim(),
          reason: revisionReason.trim(),
        }),
      });
      if (res) {
        setIsRevisionOpen(false);
        setRevisionReason("");
        // Reload transcript details to show the new revision row
        await loadTranscriptDetails(selectedAssessmentId);
      }
    } catch (e) {
      console.error("Failed to create revision", e);
      alert("Failed to create transcript revision: " + (e as Error).message);
    } finally {
      setSubmittingRevision(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-10 font-sans text-slate-900 dark:text-slate-100">
      {/* Top Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Link href="/admin" className="text-xs text-slate-500 hover:text-sky-600 transition-colors">
                ← Admin Dashboard
              </Link>
              <span className="text-slate-400">/</span>
              <span className="text-xs font-semibold text-sky-600">Pilot Telemetry</span>
            </div>
            <h1 className="text-2xl font-bold font-serif tracking-tight text-slate-900 dark:text-slate-50">
              STT Pipeline Telemetry & Pilot Kit
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
              Real-time monitoring of speech-to-text accuracy, acoustic latencies, provider cost per minute, and faithful verbatim transcript integrity.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={fetchMetrics} disabled={loading}>
              {loading ? "Refreshing..." : "↻ Refresh Telemetry"}
            </Button>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-md text-xs text-emerald-800 dark:text-emerald-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Provider: MockSTT (Zero-Vendor Mode)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto space-y-8">
        {/* KPI TELEMETRY CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Processed Audio</div>
            <div className="text-2xl font-bold font-mono mt-1 text-slate-900 dark:text-slate-50">
              {metrics ? (metrics.total_audio_seconds / 60).toFixed(1) : "0.0"} <span className="text-xs font-normal text-slate-500">mins</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">{metrics?.total_runs || 0} total recording sessions</div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Est. Provider Cost</div>
            <div className="text-2xl font-bold font-mono mt-1 text-emerald-600 dark:text-emerald-400">
              ${metrics?.total_cost_usd.toFixed(4) || "0.0000"}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">~$0.006 / audio min (Whisper)</div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Mean Latency</div>
            <div className="text-2xl font-bold font-mono mt-1 text-sky-600 dark:text-sky-400">
              {metrics ? Math.round(metrics.average_latency_ms) : 0} <span className="text-xs font-normal text-slate-500">ms</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Target &lt; 3,000ms SLA</div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Mean Confidence</div>
            <div className="text-2xl font-bold font-mono mt-1 text-slate-900 dark:text-slate-50">
              {metrics ? (metrics.average_confidence * 100).toFixed(1) : "100.0"}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Word-level acoustic certainty</div>
          </Card>

          <Card className="p-4 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Low Confidence Flags</div>
            <div className="text-2xl font-bold font-mono mt-1 text-amber-600 dark:text-amber-400">
              {metrics?.low_confidence_count || 0}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Tokens &lt; 0.70 confidence</div>
          </Card>
        </div>

        {/* MAIN SPLIT: RECENT JOBS TABLE & TRANSCRIPT INSPECTOR */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Recent STT Jobs Table */}
          <Card className="lg:col-span-7 p-5 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold">STT Execution Runs</h2>
              <Chip variant="neutral" size="sm">{metrics?.recent_jobs.length || 0} runs recorded</Chip>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-mono">
                    <th className="pb-2">Assessment ID</th>
                    <th className="pb-2">Provider / Model</th>
                    <th className="pb-2">Duration</th>
                    <th className="pb-2">Latency</th>
                    <th className="pb-2">Words</th>
                    <th className="pb-2">Conf</th>
                    <th className="pb-2 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                  {metrics?.recent_jobs.map((job) => (
                    <tr
                      key={job.metric_id}
                      className={`hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors ${
                        selectedAssessmentId === job.assessment_id ? "bg-sky-50/50 dark:bg-sky-950/30" : ""
                      }`}
                    >
                      <td className="py-2.5 font-bold text-sky-700 dark:text-sky-300">
                        {job.assessment_id.slice(0, 8)}...
                      </td>
                      <td className="py-2.5 text-slate-600 dark:text-slate-400">
                        {job.provider} <span className="text-[10px] text-slate-400">({job.model_version})</span>
                      </td>
                      <td className="py-2.5">{job.audio_duration_seconds}s</td>
                      <td className="py-2.5">{job.latency_ms}ms</td>
                      <td className="py-2.5">{job.word_count}</td>
                      <td className="py-2.5">
                        <span className={job.average_confidence >= 0.9 ? "text-emerald-600" : "text-amber-600"}>
                          {(job.average_confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-2.5 text-right font-sans">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => loadTranscriptDetails(job.assessment_id)}
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {(!metrics || metrics.recent_jobs.length === 0) && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400 font-sans">
                        No STT telemetry records yet. Recordings submitted will appear here automatically.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Transcript Details & Revision Inspector */}
          <Card className="lg:col-span-5 p-5 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
                <h2 className="text-base font-semibold">Transcript Inspector</h2>
                {transcriptData && (
                  <Chip
                    variant={transcriptData.status === "transcribed" ? "success" : "warning"}
                    size="sm"
                  >
                    {transcriptData.status}
                  </Chip>
                )}
              </div>

              {!selectedAssessmentId ? (
                <div className="py-16 text-center text-xs text-slate-400">
                  Select an assessment run from the table to inspect faithful verbatim tokens, word timestamps, and reviewer revisions.
                </div>
              ) : loadingTranscript ? (
                <div className="py-16 text-center text-xs text-slate-400 animate-pulse">
                  Loading verbatim transcript data...
                </div>
              ) : transcriptData ? (
                <div className="space-y-4">
                  {/* Research Integrity Badge */}
                  <div className="p-2.5 bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800 rounded-md text-[11px] text-sky-800 dark:text-sky-300">
                    <span className="font-bold">FAITHFUL TRANSCRIPTION:</span> Preserves disfluencies, false starts, and regional syntax without normalization.
                  </div>

                  {/* Transcript Content Box */}
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1 font-mono">
                      <span>VERBATIM TRANSCRIPT</span>
                      <span>Word Count: <strong className="text-slate-900 dark:text-slate-100">{transcriptData.word_count}</strong></span>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-sm leading-relaxed font-serif">
                      &ldquo;{transcriptData.transcript}&rdquo;
                    </div>
                  </div>

                  {/* Word Timestamps Tokens */}
                  <div>
                    <div className="text-xs text-slate-500 mb-2 font-mono">ACOUSTIC WORD TIMESTAMPS</div>
                    <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto p-2 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-200 dark:border-slate-800">
                      {transcriptData.words.map((w, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200"
                        >
                          <span className="font-bold">{w.word}</span>
                          <span className="text-[9px] text-slate-400">{w.start}s</span>
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Human Revisions List */}
                  {transcriptData.revisions.length > 0 && (
                    <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                      <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                        Human Revisions ({transcriptData.revisions.length})
                      </div>
                      <div className="space-y-2">
                        {transcriptData.revisions.map((rev) => (
                          <div
                            key={rev.revision_id}
                            className="p-2.5 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-md text-xs space-y-1"
                          >
                            <div className="font-serif italic text-slate-800 dark:text-slate-200">
                              &ldquo;{rev.revised_transcript}&rdquo;
                            </div>
                            <div className="text-[11px] text-slate-500">
                              Reason: {rev.reason} • Words: {rev.revised_word_count}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {transcriptData && (
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => setIsRevisionOpen(true)}
                >
                  + Add Human Transcript Revision
                </Button>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* HUMAN TRANSCRIPT REVISION MODAL */}
      <Dialog open={isRevisionOpen} onOpenChange={setIsRevisionOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Document Human Transcript Revision</DialogTitle>
            <DialogDescription>
              Original model outputs are strictly immutable. Your revision will be recorded as a separate review row with audit tracking.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                Revised Transcript
              </label>
              <textarea
                value={revisedText}
                onChange={(e) => setRevisedText(e.target.value)}
                rows={4}
                className="w-full mt-1.5 p-3 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:ring-1 focus:ring-sky-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase">
                Methodological Reason for Correction
              </label>
              <Input
                placeholder="e.g. Acoustic verification confirmed speaker uttered 'classes', not 'college'."
                value={revisionReason}
                onChange={(e) => setRevisionReason(e.target.value)}
                className="mt-1.5"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setIsRevisionOpen(false)} disabled={submittingRevision}>
              Cancel
            </Button>
            <Button onClick={handleCreateRevision} disabled={submittingRevision || !revisionReason.trim()}>
              {submittingRevision ? "Saving Revision..." : "Save Revision Row"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
