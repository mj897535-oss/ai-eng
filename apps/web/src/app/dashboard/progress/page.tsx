"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface CategoryComparison {
  category_code: string;
  category_name: string;
  pre_count: number;
  post_count: number;
  pre_rate_per_100: number;
  post_rate_per_100: number;
  absolute_reduction: number;
  relative_reduction_pct: number | null;
  post_status_label: string;
}

interface ComparativeSummary {
  pre_rate_per_100: number;
  post_rate_per_100: number;
  absolute_reduction: number;
  relative_reduction_pct: number | null;
  is_provisional: boolean;
  status_label: string;
  post_assessment_id: string;
  category_comparisons: CategoryComparison[];
}

interface ExplainerSection {
  term: string;
  explanation: string;
}

interface PlainLanguageExplainer {
  title: string;
  intro: string;
  sections: ExplainerSection[];
  standard_caution: string;
}

interface RepeatedPattern {
  fingerprint: string;
  category_code: string;
  normalised_form: string;
  raw_utterance: string;
  recurrence_count: number;
  first_seen: string;
  last_seen: string;
}

interface CategoryBreakdown {
  category_code: string;
  category_name: string;
  independent_count: number;
  hint_assisted_count: number;
  revealed_count: number;
  total_events: number;
  independent_rate_pct: number;
}

interface ProgressData {
  participant_code: string;
  is_results_released: boolean;
  total_practice_minutes: number;
  total_completed_sessions: number;
  independent_correction_rate_pct: number;
  repeated_error_patterns: RepeatedPattern[];
  category_breakdown: Record<string, CategoryBreakdown>;
  comparative_summary: ComparativeSummary | null;
  plain_language_explainer: PlainLanguageExplainer;
}

export default function StudentProgressPage() {
  const [data, setData] = useState<ProgressData | null>(null);
  const [showDataTable, setShowDataTable] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const res = await apiFetch<ProgressData>("/dashboard/progress");
      setData(res);
    } catch {
      // Mock fallback for standalone/demo rendering
      setData({
        participant_code: "SL-2026-0042",
        is_results_released: true,
        total_practice_minutes: 42.5,
        total_completed_sessions: 3,
        independent_correction_rate_pct: 68.2,
        repeated_error_patterns: [
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
        category_breakdown: {
          SVA: {
            category_code: "SVA",
            category_name: "Subject-Verb Agreement",
            independent_count: 5,
            hint_assisted_count: 2,
            revealed_count: 1,
            total_events: 8,
            independent_rate_pct: 62.5,
          },
          TNS: {
            category_code: "TNS",
            category_name: "Tense & Aspect",
            independent_count: 6,
            hint_assisted_count: 1,
            revealed_count: 1,
            total_events: 8,
            independent_rate_pct: 75.0,
          },
          WO: {
            category_code: "WO",
            category_name: "Word Order",
            independent_count: 4,
            hint_assisted_count: 2,
            revealed_count: 0,
            total_events: 6,
            independent_rate_pct: 66.7,
          },
        },
        comparative_summary: {
          pre_rate_per_100: 9.38,
          post_rate_per_100: 4.17,
          absolute_reduction: 5.21,
          relative_reduction_pct: 55.54,
          is_provisional: false,
          status_label: "Verified by Reviewer",
          post_assessment_id: "demo-post-id",
          category_comparisons: [
            {
              category_code: "TNS",
              category_name: "Tense & Aspect",
              pre_count: 6,
              post_count: 2,
              pre_rate_per_100: 4.69,
              post_rate_per_100: 1.67,
              absolute_reduction: 3.02,
              relative_reduction_pct: 64.39,
              post_status_label: "Observed",
            },
            {
              category_code: "SVA",
              category_name: "Subject-Verb Agreement",
              pre_count: 4,
              post_count: 0,
              pre_rate_per_100: 3.12,
              post_rate_per_100: 0.0,
              absolute_reduction: 3.12,
              relative_reduction_pct: 100.0,
              post_status_label: "Not observed in this sample",
            },
            {
              category_code: "WO",
              category_name: "Word Order",
              pre_count: 2,
              post_count: 1,
              pre_rate_per_100: 1.56,
              post_rate_per_100: 0.83,
              absolute_reduction: 0.73,
              relative_reduction_pct: 46.79,
              post_status_label: "Observed",
            },
          ],
        },
        plain_language_explainer: {
          title: "What do these numbers mean?",
          intro: "SyntaxLens evaluates your spoken English syntax during spontaneous speaking tasks.",
          sections: [
            {
              term: "Error Rate per 100 Words",
              explanation: "Instead of counting raw mistakes, we divide your errors by the total number of words you spoke and multiply by 100. This makes speaking samples of different lengths fair to compare.",
            },
            {
              term: "Observed vs Not Observed",
              explanation: "If a grammar structure had 0 errors in your post-test, we label it 'not observed in this sample'. In academic research, we never say 'mastered' because one speech sample does not prove permanent perfection.",
            },
            {
              term: "Provisional vs Verified",
              explanation: "AI first analyzes your audio, but a human research linguist reviews candidate deviations. While review is in progress, numbers are marked 'Provisional'.",
            },
            {
              term: "Descriptive Practice Metrics",
              explanation: "Practice sessions and self-correction rates describe your learning journey during tutoring. They are not official scores.",
            },
          ],
          standard_caution: "This is a descriptive comparison and does not by itself show that AI caused the change.",
        },
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
        <p className="text-slate-500 font-medium animate-pulse">Loading progress metrics...</p>
      </main>
    );
  }

  const comp = data.comparative_summary;

  return (
    <main className="min-h-screen bg-slate-50/70 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation & Header */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Link href="/dashboard" className="text-sm font-semibold text-indigo-600 hover:underline">
                &larr; Back to Student Home
              </Link>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
              Learning Progress &amp; Growth
            </h1>
            <p className="text-sm text-slate-500">
              Participant Code: <span className="font-mono font-medium text-slate-800">{data.participant_code}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDataTable(!showDataTable)}
              aria-label="Toggle accessible data table"
            >
              {showDataTable ? "Visual Charts" : "Accessible Data Table"}
            </Button>
            <Link href="/tutor">
              <Button size="sm">Resume Practice</Button>
            </Link>
          </div>
        </header>

        {/* Practice Overview KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="p-4 bg-white border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Active Practice Time
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">{data.total_practice_minutes}</span>
              <span className="text-sm text-slate-500">minutes</span>
            </div>
            <span className="text-xs text-slate-400 mt-1 block">
              Across {data.total_completed_sessions} completed session(s)
            </span>
          </Card>

          <Card className="p-4 bg-white border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Self-Correction Rate
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-emerald-600">
                {data.independent_correction_rate_pct}%
              </span>
            </div>
            <span className="text-xs text-slate-400 mt-1 block">
              Independent correction without answer reveals
            </span>
          </Card>

          <Card className="p-4 bg-white border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Evaluation Status
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              {data.is_results_released ? (
                <Chip variant={comp?.is_provisional ? "warning" : "success"}>
                  {comp?.is_provisional ? "Provisional (Review Pending)" : "Verified by Reviewer"}
                </Chip>
              ) : (
                <Chip variant="neutral">Study Protocol Blinded</Chip>
              )}
            </div>
            <span className="text-xs text-slate-400 mt-1 block">
              {data.is_results_released
                ? "Official post-test comparative report"
                : "Results masked during active evaluation"}
            </span>
          </Card>
        </div>

        {/* Comparative Evaluation Section (Pre vs Post) */}
        {data.is_results_released && comp ? (
          <section className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  Pre-Test vs Post-Test Syntax Evaluation
                  {comp.is_provisional && (
                    <Chip variant="warning">Provisional</Chip>
                  )}
                </h2>
                <p className="text-xs text-slate-500">
                  Computed via pure research metrics module per 100 spoken words.
                </p>
              </div>
              <Link href={`/assessment/${comp.post_assessment_id}/comparative`}>
                <Button variant="outline" size="sm">
                  View Full Comparative Report &rarr;
                </Button>
              </Link>
            </div>

            {/* Standard Caution Alert */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 flex items-start gap-2">
              <span className="font-bold text-amber-700">&#9888; Caution:</span>
              <span>{data.plain_language_explainer.standard_caution}</span>
            </div>

            {/* Overall Comparison Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div>
                <span className="text-xs font-semibold text-slate-400 block">Pre-Test Rate</span>
                <span className="text-xl font-bold text-slate-800 font-mono">
                  {comp.pre_rate_per_100.toFixed(2)}
                </span>
                <span className="text-[11px] text-slate-400 block">per 100 words</span>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block">Post-Test Rate</span>
                <span className="text-xl font-bold text-slate-800 font-mono">
                  {comp.post_rate_per_100.toFixed(2)}
                </span>
                <span className="text-[11px] text-slate-400 block">per 100 words</span>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block">Absolute Reduction</span>
                <span className="text-xl font-bold text-emerald-600 font-mono">
                  {comp.absolute_reduction > 0 ? `-${comp.absolute_reduction.toFixed(2)}` : `${Math.abs(comp.absolute_reduction).toFixed(2)}`}
                </span>
                <span className="text-[11px] text-slate-400 block">err / 100 words</span>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block">Relative Reduction</span>
                <span className="text-xl font-bold text-emerald-600 font-mono">
                  {comp.relative_reduction_pct !== null ? `${comp.relative_reduction_pct.toFixed(1)}%` : "N/A"}
                </span>
                <span className="text-[11px] text-slate-400 block">relative change</span>
              </div>
            </div>

            {/* Accessible Table or Visual Comparison */}
            {showDataTable ? (
              <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto shadow-xs">
                <table className="w-full text-left text-xs" aria-label="Category-level syntactic comparison">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="p-3">Category</th>
                      <th className="p-3">Pre Count</th>
                      <th className="p-3">Post Count</th>
                      <th className="p-3">Pre Rate</th>
                      <th className="p-3">Post Rate</th>
                      <th className="p-3">Abs Reduction</th>
                      <th className="p-3">Relative %</th>
                      <th className="p-3">Post Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {comp.category_comparisons.map((cat) => (
                      <tr key={cat.category_code} className="hover:bg-slate-50/50">
                        <td className="p-3 font-sans font-semibold text-slate-800">
                          {cat.category_code} &ndash; {cat.category_name}
                        </td>
                        <td className="p-3 text-slate-600">{cat.pre_count}</td>
                        <td className="p-3 text-slate-600">{cat.post_count}</td>
                        <td className="p-3 text-slate-800">{cat.pre_rate_per_100.toFixed(2)}</td>
                        <td className="p-3 text-slate-800">{cat.post_rate_per_100.toFixed(2)}</td>
                        <td className="p-3 text-emerald-600 font-semibold">{cat.absolute_reduction.toFixed(2)}</td>
                        <td className="p-3 text-emerald-600 font-semibold">
                          {cat.relative_reduction_pct !== null ? `${cat.relative_reduction_pct.toFixed(1)}%` : "N/A"}
                        </td>
                        <td className="p-3 font-sans">
                          {cat.post_count === 0 ? (
                            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[11px] font-medium">
                              Not observed in this sample
                            </span>
                          ) : (
                            <span className="text-slate-600 text-[11px]">Observed</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {comp.category_comparisons.map((cat) => {
                  const preBar = Math.min(100, (cat.pre_rate_per_100 / 12) * 100);
                  const postBar = Math.min(100, (cat.post_rate_per_100 / 12) * 100);
                  return (
                    <Card key={cat.category_code} className="p-4 bg-white border-slate-200 shadow-xs space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-slate-900">{cat.category_code}</span>
                        {cat.post_count === 0 ? (
                          <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                            Not observed in sample
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-slate-500">
                            Post: {cat.post_count} err
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500">{cat.category_name}</p>

                      <div className="space-y-1.5 pt-1">
                        <div>
                          <div className="flex justify-between text-[11px] text-slate-500 mb-0.5">
                            <span>Pre-Test Rate</span>
                            <span className="font-mono">{cat.pre_rate_per_100.toFixed(2)}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div className="bg-slate-400 h-2 rounded-full" style={{ width: `${preBar}%` }} />
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-[11px] text-slate-500 mb-0.5">
                            <span>Post-Test Rate</span>
                            <span className="font-mono font-semibold text-emerald-600">{cat.post_rate_per_100.toFixed(2)}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${postBar}%` }} />
                          </div>
                        </div>
                      </div>

                      <div className="border-t border-slate-100 pt-2 flex items-center justify-between text-xs">
                        <span className="text-slate-400">Abs. Reduction:</span>
                        <span className="font-mono font-bold text-emerald-600">
                          -{cat.absolute_reduction.toFixed(2)}
                        </span>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </section>
        ) : (
          <section className="bg-slate-100/80 border border-slate-200 rounded-xl p-6 text-center space-y-2">
            <h2 className="text-base font-bold text-slate-800">
              Comparative Pre/Post Assessment Blinded
            </h2>
            <p className="text-xs text-slate-600 max-w-lg mx-auto">
              Per the research study protocol, formal pre/post error rates remain blinded until both recordings are fully verified by researchers. This ensures unbiased speaking during your practice phase.
            </p>
          </section>
        )}

        {/* Repeated Error Patterns (Recurrence Tracker) */}
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Recurring Speech Patterns
            </h2>
            <p className="text-xs text-slate-500">
              Utterances identified across multiple turns. Repeated practice helps replace these with target structures.
            </p>
          </div>

          {data.repeated_error_patterns.length === 0 ? (
            <div className="p-4 bg-white border border-slate-200 rounded-xl text-center text-xs text-slate-500">
              No repeated syntactic patterns detected in your completed turns.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {data.repeated_error_patterns.map((pat) => (
                <div
                  key={pat.fingerprint}
                  className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                      {pat.category_code}
                    </span>
                    <span className="text-xs text-slate-500">
                      Repeated <span className="font-bold text-slate-800">{pat.recurrence_count}x</span>
                    </span>
                  </div>
                  <p className="text-sm font-mono text-slate-800 bg-slate-50 p-2 rounded border border-slate-100">
                    &ldquo;{pat.raw_utterance}&rdquo;
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Normalized: <span className="italic">{pat.normalised_form}</span>
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Plain-Language Explainer Panel (SRS Section 9) */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 space-y-4 shadow-xs">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <span className="text-indigo-600">&#9432;</span> {data.plain_language_explainer.title}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {data.plain_language_explainer.intro}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.plain_language_explainer.sections.map((sec, idx) => (
              <div key={idx} className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                  {sec.term}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed pl-3">
                  {sec.explanation}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
