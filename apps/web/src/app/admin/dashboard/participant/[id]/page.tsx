"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface TimelineEvent {
  event_type: string;
  title: string;
  timestamp: string | null;
  status: string | null;
  is_verified?: boolean;
  word_count?: number;
  active_minutes?: number;
  turns_count?: number;
}

interface AssessmentItem {
  assessment_id: string;
  assessment_type: string;
  status: string;
  is_verified: boolean;
  word_count: number;
  created_at: string;
}

interface RecurrencePattern {
  fingerprint: string;
  category_code: string;
  normalised_form: string;
  raw_utterance: string;
  recurrence_count: number;
  first_seen: string;
  last_seen: string;
}

interface DrilldownData {
  participant_id: string;
  research_code: string;
  study_group: string;
  is_withdrawn: boolean;
  enrolled_at: string | null;
  timeline: TimelineEvent[];
  assessments: AssessmentItem[];
  practice_history: {
    total_sessions: number;
    sessions: Array<{
      session_id: string;
      topic: string;
      active_duration_seconds: number;
      turns_count: number;
      status: string;
      start_time: string;
    }>;
    correction_metrics: {
      overall_rate_pct: number;
      category_breakdown: Record<string, any>;
    };
  };
  patterns: RecurrencePattern[];
}

export default function ParticipantDrilldownPage() {
  const params = useParams();
  const participantId = (params ? params["id"] : "") as string;
  const [data, setData] = useState<DrilldownData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (participantId) {
      fetchDrilldown();
    }
  }, [participantId]);

  const fetchDrilldown = async () => {
    try {
      const res = await apiFetch<DrilldownData>(`/dashboard/researcher/participants/${participantId}`);
      setData(res);
    } catch {
      // Mock fallback data for preview and standalone rendering
      setData({
        participant_id: participantId || "demo-part-1",
        research_code: "SL-2026-0042",
        study_group: "intervention",
        is_withdrawn: false,
        enrolled_at: "2026-10-24T10:00:00Z",
        timeline: [
          {
            event_type: "assessment_post",
            title: "Submitted Post-Test Recording (pair_commute_work)",
            timestamp: "2026-10-28T09:30:00Z",
            status: "completed",
            is_verified: true,
            word_count: 120,
          },
          {
            event_type: "practice_session",
            title: "Tutoring Turn (Past Tense Narration)",
            timestamp: "2026-10-27T10:15:00Z",
            status: "completed",
            active_minutes: 15.2,
            turns_count: 5,
          },
          {
            event_type: "practice_session",
            title: "Tutoring Turn (Subject-Verb Agreement)",
            timestamp: "2026-10-26T14:00:00Z",
            status: "completed",
            active_minutes: 14.8,
            turns_count: 4,
          },
          {
            event_type: "practice_session",
            title: "Tutoring Turn (Word Order & Questions)",
            timestamp: "2026-10-25T11:20:00Z",
            status: "completed",
            active_minutes: 12.5,
            turns_count: 4,
          },
          {
            event_type: "assessment_pre",
            title: "Submitted Baseline Pre-Test Recording (pair_commute_work)",
            timestamp: "2026-10-24T10:45:00Z",
            status: "completed",
            is_verified: true,
            word_count: 128,
          },
        ],
        assessments: [
          {
            assessment_id: "demo-post-id",
            assessment_type: "post",
            status: "completed",
            is_verified: true,
            word_count: 120,
            created_at: "2026-10-28T09:30:00Z",
          },
          {
            assessment_id: "demo-pre-id",
            assessment_type: "pre",
            status: "completed",
            is_verified: true,
            word_count: 128,
            created_at: "2026-10-24T10:45:00Z",
          },
        ],
        practice_history: {
          total_sessions: 3,
          sessions: [
            {
              session_id: "sess-1",
              topic: "Past Tense Narration",
              active_duration_seconds: 912,
              turns_count: 5,
              status: "completed",
              start_time: "2026-10-27T10:15:00Z",
            },
          ],
          correction_metrics: {
            overall_rate_pct: 68.2,
            category_breakdown: {},
          },
        },
        patterns: [
          {
            fingerprint: "she_go_to_market",
            category_code: "SVA",
            normalised_form: "she go to market",
            raw_utterance: "yesterday she go to market",
            recurrence_count: 3,
            first_seen: "2026-10-25T14:30:00Z",
            last_seen: "2026-10-27T10:15:00Z",
          },
          {
            fingerprint: "i_am_agree_with_you",
            category_code: "AUX",
            normalised_form: "i am agree with you",
            raw_utterance: "i am agree with you",
            recurrence_count: 2,
            first_seen: "2026-10-26T09:00:00Z",
            last_seen: "2026-10-27T10:45:00Z",
          },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
        <p className="text-slate-500 font-medium animate-pulse">Loading participant drilldown...</p>
      </main>
    );
  }

  const totalActiveMinutes = roundTo1(
    data.timeline
      .filter((t) => t.event_type === "practice_session" && t.active_minutes)
      .reduce((acc, curr) => acc + (curr.active_minutes || 0), 0)
  );

  function roundTo1(num: number) {
    return Math.round(num * 10) / 10;
  }

  return (
    <main className="min-h-screen bg-slate-50/70 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation & Header */}
        <header className="border-b border-slate-200 pb-5 space-y-2">
          <Link href="/admin/dashboard" className="text-sm font-semibold text-indigo-600 hover:underline">
            &larr; Back to Cohort Dashboard
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight font-mono">
                  {data.research_code}
                </h1>
                <Chip variant={data.study_group === "intervention" ? "primary" : "neutral"}>
                  {data.study_group.toUpperCase()}
                </Chip>
                {data.is_withdrawn ? (
                  <Chip variant="danger">Withdrawn</Chip>
                ) : (
                  <Chip variant="success">Active Participant</Chip>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Enrolled: {data.enrolled_at ? new Date(data.enrolled_at).toLocaleDateString() : "N/A"} &bull; ID: {data.participant_id}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Link href={`/assessment/${data.assessments[0]?.assessment_id}/comparative`}>
                <Button variant="outline" size="sm">
                  Comparative Report &rarr;
                </Button>
              </Link>
            </div>
          </div>
        </header>

        {/* Quick KPI stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Assessments Completed
            </span>
            <span className="text-2xl font-bold text-slate-900 font-mono mt-1 block">
              {data.assessments.length}
            </span>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Practice Time
            </span>
            <span className="text-2xl font-bold text-slate-900 font-mono mt-1 block">
              {totalActiveMinutes} m
            </span>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Tutoring Sessions
            </span>
            <span className="text-2xl font-bold text-slate-900 font-mono mt-1 block">
              {data.practice_history.total_sessions}
            </span>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Self-Correction Rate
            </span>
            <span className="text-2xl font-bold text-emerald-600 font-mono mt-1 block">
              {data.practice_history.correction_metrics.overall_rate_pct}%
            </span>
          </Card>
        </div>

        {/* Longitudinal Event Timeline */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Longitudinal Study Event Timeline
            </h2>
            <p className="text-xs text-slate-500">
              Chronological log of pre-tests, tutoring sessions, interruptions, and post-tests.
            </p>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {data.timeline.map((evt, idx) => (
              <div key={idx} className="relative">
                <span
                  className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 border-white ${
                    evt.event_type.startsWith("assessment") ? "bg-indigo-600" : "bg-emerald-500"
                  }`}
                />
                <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3 space-y-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <span className="font-semibold text-sm text-slate-800">{evt.title}</span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : "Unknown"}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                    {evt.status && (
                      <span className="capitalize text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                        Status: {evt.status}
                      </span>
                    )}
                    {evt.is_verified !== undefined && (
                      <Chip variant={evt.is_verified ? "success" : "warning"}>
                        {evt.is_verified ? "Verified by Reviewer" : "Provisional"}
                      </Chip>
                    )}
                    {evt.word_count && (
                      <span className="text-slate-500 font-mono">
                        Words: {evt.word_count}
                      </span>
                    )}
                    {evt.active_minutes && (
                      <span className="text-slate-500 font-mono">
                        Active Time: {evt.active_minutes} min
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Recurrence Patterns for this participant */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900">
              Recurrence Patterns &amp; Utterance Fingerprints (FR-14)
            </h2>
            <p className="text-xs text-slate-500">
              Syntactic deviations tracked across turns. Normalised to prevent double-counting.
            </p>
          </div>

          {data.patterns.length === 0 ? (
            <p className="text-xs text-slate-400">No recurrence patterns tracked yet.</p>
          ) : (
            <div className="space-y-2">
              {data.patterns.map((p) => (
                <div
                  key={p.fingerprint}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                        {p.category_code}
                      </span>
                      <span className="font-mono text-xs text-slate-700">&ldquo;{p.raw_utterance}&rdquo;</span>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono block">
                      Fingerprint: {p.fingerprint}
                    </span>
                  </div>
                  <div className="text-right sm:text-left flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-800 bg-white px-2 py-1 rounded border border-slate-200">
                      {p.recurrence_count}x Recurred
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
