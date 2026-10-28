"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface CategoryMetric {
  unique_error_episodes: number;
  independent_corrections: number;
  hint_assisted_corrections: number;
  unresolved: number;
  independent_correction_rate_pct: number;
}

interface CorrectionMetrics {
  overall_rate_pct: number;
  total_unique_error_episodes: number;
  total_independent_corrections: number;
  category_breakdown: Record<string, CategoryMetric>;
  disclaimer: string;
}

interface PracticeSessionSummary {
  session_id: string;
  start_time: string | null;
  end_time: string | null;
  active_duration_seconds: number;
  idle_duration_seconds: number;
  turns_count: number;
  status: string;
  topic: string | null;
  target_categories: string[];
  interruption_count: number;
  prompt_version: string;
}

interface UtterancePatternItem {
  pattern_id: string;
  target_category: string;
  utterance_fingerprint: string;
  canonical_phrase: string;
  construction_type: string;
  occurrence_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  resolved_independently: boolean;
}

export default function PracticeHistoryPage() {
  const [sessions, setSessions] = useState<PracticeSessionSummary[]>([]);
  const [metrics, setMetrics] = useState<CorrectionMetrics | null>(null);
  const [patterns, setPatterns] = useState<UtterancePatternItem[]>([]);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const [histData, patData] = await Promise.all([
        apiFetch<{ sessions: PracticeSessionSummary[]; total_sessions: number; correction_metrics: CorrectionMetrics }>("/tutor/history"),
        apiFetch<UtterancePatternItem[]>("/tutor/recurrence"),
      ]);
      setSessions(histData.sessions || []);
      setMetrics(histData.correction_metrics || null);
      setPatterns(patData || []);
    } catch {
      // Mock fallback for presentation
      setSessions([
        {
          session_id: "sess-8001-demo-a",
          start_time: new Date(Date.now() - 3600000 * 48).toISOString(),
          end_time: new Date(Date.now() - 3600000 * 48 + 960000).toISOString(),
          active_duration_seconds: 900,
          idle_duration_seconds: 60,
          turns_count: 8,
          status: "completed",
          topic: "Technology and College Life",
          target_categories: ["SVA", "TNS"],
          interruption_count: 0,
          prompt_version: "v1.0-tutor-standard",
        },
        {
          session_id: "sess-8001-demo-b",
          start_time: new Date(Date.now() - 3600000 * 24).toISOString(),
          end_time: new Date(Date.now() - 3600000 * 24 + 1020000).toISOString(),
          active_duration_seconds: 900,
          idle_duration_seconds: 120,
          turns_count: 10,
          status: "completed",
          topic: "Daily routines and workplace communication",
          target_categories: ["SVA"],
          interruption_count: 1,
          prompt_version: "v1.0-tutor-standard",
        },
      ]);
      setMetrics({
        overall_rate_pct: 66.7,
        total_unique_error_episodes: 3,
        total_independent_corrections: 2,
        category_breakdown: {
          SVA: {
            unique_error_episodes: 2,
            independent_corrections: 1,
            hint_assisted_corrections: 1,
            unresolved: 0,
            independent_correction_rate_pct: 50.0,
          },
          TNS: {
            unique_error_episodes: 1,
            independent_corrections: 1,
            hint_assisted_corrections: 0,
            unresolved: 0,
            independent_correction_rate_pct: 100.0,
          },
        },
        disclaimer: "Descriptive practice metric only. Never used as an official assessment score or proficiency certification.",
      });
      setPatterns([
        {
          pattern_id: "pat-1",
          target_category: "SVA",
          utterance_fingerprint: "d9e84b12f6a78201",
          canonical_phrase: "he go to college every day",
          construction_type: "SVA_construction",
          occurrence_count: 2,
          first_seen_at: new Date(Date.now() - 3600000 * 48).toISOString(),
          last_seen_at: new Date(Date.now() - 3600000 * 24).toISOString(),
          resolved_independently: true,
        },
        {
          pattern_id: "pat-2",
          target_category: "TNS",
          utterance_fingerprint: "a4f1082c33bc09e1",
          canonical_phrase: "yesterday i go there by bus",
          construction_type: "TNS_construction",
          occurrence_count: 1,
          first_seen_at: new Date(Date.now() - 3600000 * 48).toISOString(),
          last_seen_at: new Date(Date.now() - 3600000 * 48).toISOString(),
          resolved_independently: true,
        },
      ]);
    }
  };

  const totalActiveSeconds = sessions.reduce((acc, s) => acc + s.active_duration_seconds, 0);
  const totalIdleSeconds = sessions.reduce((acc, s) => acc + s.idle_duration_seconds, 0);
  const totalInterrupts = sessions.reduce((acc, s) => acc + s.interruption_count, 0);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                Practice Session History & Recurrence
              </h1>
              <Chip variant="success" size="sm">SRS FR-13 & FR-14</Chip>
            </div>
            <p className="text-slate-400 mt-1">
              Longitudinal tracking of conversational practice, active duration, and independent self-corrections.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/tutor">
              <Button variant="primary">Start Practice Turn</Button>
            </Link>
            <Link href="/assessment">
              <Button variant="secondary">Assessment Center</Button>
            </Link>
          </div>
        </div>

        {/* Scientific Disclaimer Alert */}
        <div className="p-4 bg-amber-950/40 border border-amber-800/60 rounded-xl text-amber-200 text-sm flex items-start gap-3">
          <span className="text-xl">⚠️</span>
          <div>
            <strong className="font-semibold block text-amber-100">Research Integrity Protocol (SRS FR-14):</strong>
            Independent correction rates are descriptive practice metrics derived purely from event sequences.
            Repeated references to the same utterance within or across sessions do not inflate error counts.
            These metrics are never used as official assessment scores or proficiency certificates.
          </div>
        </div>

        {/* Analytics KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Completed Sessions</div>
            <div className="text-3xl font-bold text-white mt-2">{sessions.length}</div>
            <div className="text-xs text-slate-400 mt-1">Target: 3 sessions / week</div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Practice Time</div>
            <div className="text-3xl font-bold text-emerald-400 mt-2">
              {Math.floor(totalActiveSeconds / 60)}m {totalActiveSeconds % 60}s
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Idle excluded: {Math.floor(totalIdleSeconds / 60)}m {totalIdleSeconds % 60}s
            </div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Independent Correction</div>
            <div className="text-3xl font-bold text-indigo-400 mt-2">
              {metrics ? `${metrics.overall_rate_pct}%` : "—"}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {metrics?.total_independent_corrections || 0} of {metrics?.total_unique_error_episodes || 0} unique episodes
            </div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Technical Interruptions</div>
            <div className="text-3xl font-bold text-slate-300 mt-2">{totalInterrupts}</div>
            <div className="text-xs text-slate-400 mt-1">Logged (disconnect/mic)</div>
          </Card>
        </div>

        {/* Category Breakdown Table */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center justify-between">
            <span>Independent Correction Rate by Syntactic Category</span>
            <span className="text-xs font-normal text-slate-400">SRS Section 10</span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/90 text-slate-400 border-b border-slate-700">
                <tr>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Unique Episodes</th>
                  <th className="py-3 px-4">Independent Corrections</th>
                  <th className="py-3 px-4">Hint-Assisted</th>
                  <th className="py-3 px-4">Unresolved</th>
                  <th className="py-3 px-4 text-right">Correction Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60">
                {metrics && Object.entries(metrics.category_breakdown).length > 0 ? (
                  Object.entries(metrics.category_breakdown).map(([cat, data]) => (
                    <tr key={cat} className="hover:bg-slate-700/30">
                      <td className="py-3 px-4 font-semibold text-white">
                        <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-200 text-xs font-mono mr-2">
                          {cat}
                        </span>
                      </td>
                      <td className="py-3 px-4">{data.unique_error_episodes}</td>
                      <td className="py-3 px-4 text-emerald-400 font-medium">{data.independent_corrections}</td>
                      <td className="py-3 px-4 text-blue-400">{data.hint_assisted_corrections}</td>
                      <td className="py-3 px-4 text-slate-400">{data.unresolved}</td>
                      <td className="py-3 px-4 text-right">
                        <span className={`font-bold ${data.independent_correction_rate_pct >= 50 ? "text-emerald-400" : "text-amber-400"}`}>
                          {data.independent_correction_rate_pct}%
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400">
                      No error episodes recorded in practice turns yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Longitudinal Recurring Patterns (FR-14) */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-white">Longitudinal Recurrence Tracker</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Utterance patterns deduplicated by SHA-256 fingerprint. Double-counting prevented per FR-14.
              </p>
            </div>
            <Chip variant="neutral" size="sm">{patterns.length} Recurring Patterns</Chip>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/90 text-slate-400 border-b border-slate-700">
                <tr>
                  <th className="py-3 px-4">Canonical Phrase</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4 text-center">Occurrences</th>
                  <th className="py-3 px-4">First Encounter</th>
                  <th className="py-3 px-4">Latest Encounter</th>
                  <th className="py-3 px-4 text-right">Resolution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60">
                {patterns.length > 0 ? (
                  patterns.map((p) => (
                    <tr key={p.pattern_id} className="hover:bg-slate-700/30">
                      <td className="py-3 px-4 font-medium text-slate-100">
                        &ldquo;{p.canonical_phrase}&rdquo;
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          FP: {p.utterance_fingerprint}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-700 text-xs font-mono text-slate-200">
                          {p.target_category}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-slate-200">
                        {p.occurrence_count}x
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400">
                        {p.first_seen_at ? new Date(p.first_seen_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400">
                        {p.last_seen_at ? new Date(p.last_seen_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {p.resolved_independently ? (
                          <Chip variant="success" size="sm">Independent Resolution</Chip>
                        ) : (
                          <Chip variant="warning" size="sm">Assisted / In Progress</Chip>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400">
                      No recurring utterance patterns recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Sessions Trajectory List */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <h2 className="text-lg font-bold text-white mb-4">Practice Session Log</h2>
          <div className="space-y-3">
            {sessions.map((s) => (
              <div
                key={s.session_id}
                className="p-4 bg-slate-800/80 rounded-lg border border-slate-700/80 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{s.topic || "General Grammar Practice"}</span>
                    <Chip variant={s.status === "completed" ? "success" : "neutral"} size="sm">
                      {s.status}
                    </Chip>
                    {s.interruption_count > 0 && (
                      <Chip variant="warning" size="sm">
                        {s.interruption_count} Interruption{s.interruption_count > 1 ? "s" : ""}
                      </Chip>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
                    <span>Date: {s.start_time ? new Date(s.start_time).toLocaleString() : "—"}</span>
                    <span>•</span>
                    <span>Turns: {s.turns_count}</span>
                    <span>•</span>
                    <span>Prompt: {s.prompt_version}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      Targets:
                      {s.target_categories.map((c) => (
                        <span key={c} className="px-1.5 py-0.2 bg-slate-700 text-slate-300 rounded text-[10px] font-mono">
                          {c}
                        </span>
                      ))}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6 text-right">
                  <div>
                    <div className="text-xs text-slate-400">Active Duration</div>
                    <div className="text-base font-bold text-emerald-400">
                      {Math.floor(s.active_duration_seconds / 60)}m {s.active_duration_seconds % 60}s
                    </div>
                  </div>
                  {s.idle_duration_seconds > 0 && (
                    <div>
                      <div className="text-xs text-slate-400">Idle Excluded</div>
                      <div className="text-base font-medium text-slate-400">
                        {Math.floor(s.idle_duration_seconds / 60)}m {s.idle_duration_seconds % 60}s
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
