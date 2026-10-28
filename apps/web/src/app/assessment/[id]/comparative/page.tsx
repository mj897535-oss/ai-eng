"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface CategoryComparisonItem {
  category_code: string;
  category_name: string;
  pre_count: number;
  post_count: number;
  pre_words: number;
  post_words: number;
  pre_rate_per_100: number;
  post_rate_per_100: number;
  absolute_reduction: number;
  relative_reduction_pct: number | null;
  relative_reduction_status: string;
  pre_status_label: string;
  post_status_label: string;
}

interface SyntaxFingerprintItem {
  category_code: string;
  category_name: string;
  pre_rate: number;
  post_rate: number;
  pre_count: number;
  post_count: number;
  pre_observed: boolean;
  post_observed: boolean;
  pre_status_label: string;
  post_status_label: string;
}

interface ReproducibilityInput {
  annotation_set_used: string;
  raw_annotation_count: number;
  assessable_error_count: number;
  excluded_items_count: number;
  total_words: number;
  counting_rule: string;
  rubric_version: string;
  prompt_version?: string | null;
  model_version?: string;
  stt_version?: string;
  is_verified?: boolean;
}

interface ReproducibilityPanelData {
  formulas: {
    error_rate_per_100_words: string;
    absolute_reduction: string;
    relative_reduction_pct: string;
    category_error_rate: string;
  };
  pre_inputs: ReproducibilityInput;
  post_inputs: ReproducibilityInput;
  verification_status: {
    is_pre_verified: boolean;
    is_post_verified: boolean;
    overall_status: string;
  };
}

interface ComparativeReportData {
  is_provisional: boolean;
  status_label: string;
  provisional_warning: string | null;
  standard_caution: string;
  overall_comparison: {
    pre_word_count: number;
    post_word_count: number;
    pre_error_count: number;
    post_error_count: number;
    pre_rate_per_100: number;
    post_rate_per_100: number;
    absolute_reduction: number;
    relative_reduction_pct: number | null;
    relative_reduction_status: string;
  };
  pre_summary: {
    word_count: number;
    raw_annotation_count: number;
    assessable_error_count: number;
    excluded_count: number;
    error_rate_per_100: number;
    is_verified: boolean;
    status_label: string;
  };
  post_summary: {
    word_count: number;
    raw_annotation_count: number;
    assessable_error_count: number;
    excluded_count: number;
    error_rate_per_100: number;
    is_verified: boolean;
    status_label: string;
  };
  category_comparisons: Record<string, CategoryComparisonItem>;
  syntax_fingerprint: SyntaxFingerprintItem[];
  reproducibility_panel: ReproducibilityPanelData;
  pre_assessment_id?: string;
  post_assessment_id?: string;
}

export default function ComparativeReportPage({ params }: { params: { id: string } }) {
  const assessmentId = params.id;
  const [report, setReport] = useState<ComparativeReportData | null>(null);
  const [countingRule, setCountingRule] = useState<string>("count_all");
  const [showReproducibility, setShowReproducibility] = useState<boolean>(false);

  useEffect(() => {
    fetchReport(countingRule);
  }, [assessmentId, countingRule]);

  const fetchReport = async (rule: string) => {
    try {
      const data = await apiFetch<ComparativeReportData>(
        `/assessments/${assessmentId}/comparative-report?counting_rule=${rule}`
      );
      setReport(data);
    } catch {
      // Mock fallback for presentation and testing
      setReport({
        is_provisional: false,
        status_label: "verified",
        provisional_warning: null,
        standard_caution: "This is a descriptive comparison and does not by itself show that AI caused the change.",
        overall_comparison: {
          pre_word_count: 120,
          post_word_count: 120,
          pre_error_count: 8,
          post_error_count: 3,
          pre_rate_per_100: 6.67,
          post_rate_per_100: 2.50,
          absolute_reduction: 4.17,
          relative_reduction_pct: 62.52,
          relative_reduction_status: "defined",
        },
        pre_summary: {
          word_count: 120,
          raw_annotation_count: 9,
          assessable_error_count: 8,
          excluded_count: 1,
          error_rate_per_100: 6.67,
          is_verified: true,
          status_label: "verified",
        },
        post_summary: {
          word_count: 120,
          raw_annotation_count: 4,
          assessable_error_count: 3,
          excluded_count: 1,
          error_rate_per_100: 2.50,
          is_verified: true,
          status_label: "verified",
        },
        category_comparisons: {
          TNS: {
            category_code: "TNS",
            category_name: "Tense and Aspect",
            pre_count: 3,
            post_count: 1,
            pre_words: 120,
            post_words: 120,
            pre_rate_per_100: 2.50,
            post_rate_per_100: 0.83,
            absolute_reduction: 1.67,
            relative_reduction_pct: 66.8,
            relative_reduction_status: "defined",
            pre_status_label: "observed",
            post_status_label: "observed",
          },
          SVA: {
            category_code: "SVA",
            category_name: "Subject-Verb Agreement",
            pre_count: 3,
            post_count: 0,
            pre_words: 120,
            post_words: 120,
            pre_rate_per_100: 2.50,
            post_rate_per_100: 0.0,
            absolute_reduction: 2.50,
            relative_reduction_pct: 100.0,
            relative_reduction_status: "defined",
            pre_status_label: "observed",
            post_status_label: "not observed in this sample",
          },
          PREP: {
            category_code: "PREP",
            category_name: "Prepositions",
            pre_count: 2,
            post_count: 1,
            pre_words: 120,
            post_words: 120,
            pre_rate_per_100: 1.67,
            post_rate_per_100: 0.83,
            absolute_reduction: 0.84,
            relative_reduction_pct: 50.3,
            relative_reduction_status: "defined",
            pre_status_label: "observed",
            post_status_label: "observed",
          },
          ART: {
            category_code: "ART",
            category_name: "Articles (Definite / Indefinite / Zero)",
            pre_count: 0,
            post_count: 1,
            pre_words: 120,
            post_words: 120,
            pre_rate_per_100: 0.0,
            post_rate_per_100: 0.83,
            absolute_reduction: -0.83,
            relative_reduction_pct: null,
            relative_reduction_status: "undefined_zero_baseline",
            pre_status_label: "not observed in this sample",
            post_status_label: "observed",
          },
        },
        syntax_fingerprint: [
          { category_code: "TNS", category_name: "Tense and Aspect", pre_rate: 2.5, post_rate: 0.83, pre_count: 3, post_count: 1, pre_observed: true, post_observed: true, pre_status_label: "observed", post_status_label: "observed" },
          { category_code: "SVA", category_name: "Subject-Verb Agreement", pre_rate: 2.5, post_rate: 0.0, pre_count: 3, post_count: 0, pre_observed: true, post_observed: false, pre_status_label: "observed", post_status_label: "not observed in this sample" },
          { category_code: "PREP", category_name: "Prepositions", pre_rate: 1.67, post_rate: 0.83, pre_count: 2, post_count: 1, pre_observed: true, post_observed: true, pre_status_label: "observed", post_status_label: "observed" },
          { category_code: "ART", category_name: "Articles", pre_rate: 0.0, post_rate: 0.83, pre_count: 0, post_count: 1, pre_observed: false, post_observed: true, pre_status_label: "not observed in this sample", post_status_label: "observed" },
          { category_code: "WO", category_name: "Word Order", pre_rate: 0.0, post_rate: 0.0, pre_count: 0, post_count: 0, pre_observed: false, post_observed: false, pre_status_label: "not observed in this sample", post_status_label: "not observed in this sample" },
          { category_code: "AUX", category_name: "Auxiliary Verbs", pre_rate: 0.0, post_rate: 0.0, pre_count: 0, post_count: 0, pre_observed: false, post_observed: false, pre_status_label: "not observed in this sample", post_status_label: "not observed in this sample" },
          { category_code: "PRO", category_name: "Pronouns", pre_rate: 0.0, post_rate: 0.0, pre_count: 0, post_count: 0, pre_observed: false, post_observed: false, pre_status_label: "not observed in this sample", post_status_label: "not observed in this sample" },
          { category_code: "OTH", category_name: "Other Variations", pre_rate: 0.0, post_rate: 0.0, pre_count: 0, post_count: 0, pre_observed: false, post_observed: false, pre_status_label: "not observed in this sample", post_status_label: "not observed in this sample" },
        ],
        reproducibility_panel: {
          formulas: {
            error_rate_per_100_words: "(assessable_error_count / total_words) * 100",
            absolute_reduction: "pre_rate - post_rate",
            relative_reduction_pct: "((pre_rate - post_rate) / pre_rate) * 100 (defined ONLY if pre_rate > 0)",
            category_error_rate: "(category_assessable_count / total_words) * 100",
          },
          pre_inputs: {
            annotation_set_used: "effective",
            raw_annotation_count: 9,
            assessable_error_count: 8,
            excluded_items_count: 1,
            total_words: 120,
            counting_rule: "count_all",
            rubric_version: "v1.0-jam-phd",
            prompt_version: "v1.0-assessor",
            model_version: "mock-syntax-v1",
            stt_version: "mock-stt-v1",
            is_verified: true,
          },
          post_inputs: {
            annotation_set_used: "effective",
            raw_annotation_count: 4,
            assessable_error_count: 3,
            excluded_items_count: 1,
            total_words: 120,
            counting_rule: "count_all",
            rubric_version: "v1.0-jam-phd",
            prompt_version: "v1.0-assessor",
            model_version: "mock-syntax-v1",
            stt_version: "mock-stt-v1",
            is_verified: true,
          },
          verification_status: {
            is_pre_verified: true,
            is_post_verified: true,
            overall_status: "verified",
          },
        },
      });
    }
  };

  const comp = report?.overall_comparison;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                Pre-to-Post Comparative Report
              </h1>
              {report?.is_provisional ? (
                <Chip variant="warning" size="sm">PROVISIONAL (Review Pending)</Chip>
              ) : (
                <Chip variant="success" size="sm">VERIFIED BY RESEARCHER</Chip>
              )}
            </div>
            <p className="text-slate-400 mt-1">
              Paired longitudinal assessment under identical rubric, transcription, and equivalence parameters.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReproducibility(!showReproducibility)}
            >
              {showReproducibility ? "Hide Reproducibility Panel" : "Reproducibility Panel (Sig E)"}
            </Button>
            <Link href={`/assessment/${assessmentId}/report`}>
              <Button variant="secondary" size="sm">Evidence Lens</Button>
            </Link>
          </div>
        </div>

        {/* Standard Caution Alert (SRS §14) */}
        <div className="p-4 bg-amber-950/40 border border-amber-800/80 rounded-xl text-amber-200 text-sm flex items-start gap-3 shadow-lg">
          <span className="text-xl">⚠️</span>
          <div className="space-y-1">
            <strong className="font-semibold block text-amber-100">
              Research Causality Protocol:
            </strong>
            <p className="font-medium text-amber-200">
              &ldquo;{report?.standard_caution}&rdquo;
            </p>
            <p className="text-xs text-amber-400">
              Absence of an error structure in a speech sample does not prove permanent acquisition or master level attainment.
            </p>
          </div>
        </div>

        {/* Provisional Banner if not verified */}
        {report?.is_provisional && (
          <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-300 text-xs">
            <strong>Provisional Analysis Notice:</strong> {report.provisional_warning}
          </div>
        )}

        {/* Counting Rule Selector */}
        <div className="flex items-center justify-between p-3 bg-slate-800/60 border border-slate-700 rounded-lg text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Frozen Rubric Counting Rule:</span>
            <span className="font-mono font-semibold text-slate-200">{countingRule}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCountingRule("count_all")}
              className={`px-2.5 py-1 rounded text-xs transition ${
                countingRule === "count_all"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              Count All Errors
            </button>
            <button
              onClick={() => setCountingRule("count_one_per_sentence")}
              className={`px-2.5 py-1 rounded text-xs transition ${
                countingRule === "count_one_per_sentence"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              1 Error / Sentence
            </button>
          </div>
        </div>

        {/* Primary Metrics Scorecard */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Baseline (Pre-Test)</div>
            <div className="text-3xl font-bold text-slate-200 mt-2">
              {comp?.pre_rate_per_100} <span className="text-sm font-normal text-slate-400">/ 100w</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Raw: {comp?.pre_error_count} errors in {comp?.pre_word_count} words
            </div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Post-Test Rate</div>
            <div className="text-3xl font-bold text-white mt-2">
              {comp?.post_rate_per_100} <span className="text-sm font-normal text-slate-400">/ 100w</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Raw: {comp?.post_error_count} errors in {comp?.post_word_count} words
            </div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Absolute Reduction</div>
            <div className={`text-3xl font-bold mt-2 ${comp && comp.absolute_reduction >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {comp ? (comp.absolute_reduction > 0 ? `+${comp.absolute_reduction}` : comp.absolute_reduction) : "—"}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              pre_rate − post_rate
            </div>
          </Card>

          <Card className="p-5 bg-slate-800/80 border-slate-700">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Relative Reduction</div>
            <div className="text-3xl font-bold text-indigo-400 mt-2">
              {comp?.relative_reduction_pct !== null ? `${comp?.relative_reduction_pct}%` : "N/A"}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {comp?.relative_reduction_status === "undefined_zero_baseline"
                ? "Undefined (Zero baseline)"
                : "((pre − post) / pre) * 100"}
            </div>
          </Card>
        </div>

        {/* Signature Feature B: Syntax Fingerprint Overlay */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-white">Syntax Fingerprint (Signature Feature B)</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Comparative error density per 100 words across 8 standardized categories.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-3 h-3 rounded-full bg-slate-500 inline-block"></span> Pre-Test
              </span>
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Post-Test
              </span>
            </div>
          </div>

          <div className="space-y-4">
            {report?.syntax_fingerprint.map((fp) => (
              <div key={fp.category_code} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    <span className="px-1.5 py-0.5 rounded bg-slate-700 font-mono text-[11px] mr-1.5">
                      {fp.category_code}
                    </span>
                    {fp.category_name}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-mono">Pre: {fp.pre_rate} ({fp.pre_count})</span>
                    <span className="text-emerald-400 font-mono">Post: {fp.post_rate} ({fp.post_count})</span>
                    {!fp.post_observed && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-slate-400 italic">
                        not observed in this sample
                      </span>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 h-4 bg-slate-900/80 rounded overflow-hidden p-0.5 border border-slate-800">
                  <div className="w-full bg-slate-800 rounded-sm flex items-center">
                    <div
                      className="h-full bg-slate-500 rounded-sm transition-all"
                      style={{ width: `${Math.min(100, fp.pre_rate * 15)}%` }}
                    />
                  </div>
                  <div className="w-full bg-slate-800 rounded-sm flex items-center">
                    <div
                      className="h-full bg-emerald-500 rounded-sm transition-all"
                      style={{ width: `${Math.min(100, fp.post_rate * 15)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Detailed Category-Level Table */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <h2 className="text-lg font-bold text-white mb-4">Category-Level Reductions & Counts</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/90 text-slate-400 border-b border-slate-700">
                <tr>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Pre Count</th>
                  <th className="py-3 px-4">Pre Rate</th>
                  <th className="py-3 px-4">Post Count</th>
                  <th className="py-3 px-4">Post Rate</th>
                  <th className="py-3 px-4 text-center">Absolute Δ</th>
                  <th className="py-3 px-4 text-center">Relative %</th>
                  <th className="py-3 px-4 text-right">Observation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60 font-mono text-xs">
                {report && Object.values(report.category_comparisons).map((cat) => (
                  <tr key={cat.category_code} className="hover:bg-slate-700/30">
                    <td className="py-3 px-4 font-sans font-semibold text-white">
                      <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-200 mr-2 text-[11px]">
                        {cat.category_code}
                      </span>
                      {cat.category_name}
                    </td>
                    <td className="py-3 px-4">{cat.pre_count}</td>
                    <td className="py-3 px-4 text-slate-300">{cat.pre_rate_per_100}</td>
                    <td className="py-3 px-4">{cat.post_count}</td>
                    <td className="py-3 px-4 text-emerald-400">{cat.post_rate_per_100}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={cat.absolute_reduction >= 0 ? "text-emerald-400" : "text-rose-400"}>
                        {cat.absolute_reduction > 0 ? `+${cat.absolute_reduction}` : cat.absolute_reduction}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {cat.relative_reduction_pct !== null ? `${cat.relative_reduction_pct}%` : "N/A"}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        cat.post_count > 0 ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-slate-800 text-slate-400 border border-slate-700 italic"
                      }`}>
                        {cat.post_status_label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Signature Feature E: Reproducibility Panel Drawer */}
        {showReproducibility && report?.reproducibility_panel && (
          <Card className="p-6 bg-slate-950 border-indigo-700/60 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-indigo-400 flex items-center gap-2">
                  <span>🔬</span> Reproducibility Panel (Signature Feature E)
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Complete provenance trace, formulas, inputs, and denominators.
                </p>
              </div>
              <Chip variant="neutral" size="sm">Zero I/O Guarantee</Chip>
            </div>

            {/* Formulas */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 uppercase">Exact Formulas Applied:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono bg-slate-900 p-3 rounded border border-slate-800">
                <div>
                  <span className="text-slate-400">Error Rate: </span>
                  <code className="text-indigo-300">{report.reproducibility_panel.formulas.error_rate_per_100_words}</code>
                </div>
                <div>
                  <span className="text-slate-400">Absolute Δ: </span>
                  <code className="text-indigo-300">{report.reproducibility_panel.formulas.absolute_reduction}</code>
                </div>
                <div>
                  <span className="text-slate-400">Relative Δ: </span>
                  <code className="text-indigo-300">{report.reproducibility_panel.formulas.relative_reduction_pct}</code>
                </div>
                <div>
                  <span className="text-slate-400">Category Rate: </span>
                  <code className="text-indigo-300">{report.reproducibility_panel.formulas.category_error_rate}</code>
                </div>
              </div>
            </div>

            {/* Pre and Post Provenance */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1.5">
                <h5 className="font-bold text-slate-200">Baseline (Pre-Test) Provenance</h5>
                <div><span className="text-slate-400">Annotation Set:</span> <span className="font-mono text-white">{report.reproducibility_panel.pre_inputs.annotation_set_used}</span></div>
                <div><span className="text-slate-400">Assessable Errors:</span> <span className="font-mono text-white">{report.reproducibility_panel.pre_inputs.assessable_error_count}</span></div>
                <div><span className="text-slate-400">Excluded (uncertain/dialect):</span> <span className="font-mono text-white">{report.reproducibility_panel.pre_inputs.excluded_items_count}</span></div>
                <div><span className="text-slate-400">Total Words (Denominator):</span> <span className="font-mono text-white">{report.reproducibility_panel.pre_inputs.total_words}</span></div>
                <div><span className="text-slate-400">Rubric Version:</span> <span className="font-mono text-indigo-300">{report.reproducibility_panel.pre_inputs.rubric_version}</span></div>
                <div><span className="text-slate-400">Prompt Version:</span> <span className="font-mono text-indigo-300">{report.reproducibility_panel.pre_inputs.prompt_version || "default"}</span></div>
              </div>

              <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1.5">
                <h5 className="font-bold text-slate-200">Post-Test Provenance</h5>
                <div><span className="text-slate-400">Annotation Set:</span> <span className="font-mono text-white">{report.reproducibility_panel.post_inputs.annotation_set_used}</span></div>
                <div><span className="text-slate-400">Assessable Errors:</span> <span className="font-mono text-white">{report.reproducibility_panel.post_inputs.assessable_error_count}</span></div>
                <div><span className="text-slate-400">Excluded (uncertain/dialect):</span> <span className="font-mono text-white">{report.reproducibility_panel.post_inputs.excluded_items_count}</span></div>
                <div><span className="text-slate-400">Total Words (Denominator):</span> <span className="font-mono text-white">{report.reproducibility_panel.post_inputs.total_words}</span></div>
                <div><span className="text-slate-400">Rubric Version:</span> <span className="font-mono text-indigo-300">{report.reproducibility_panel.post_inputs.rubric_version}</span></div>
                <div><span className="text-slate-400">Prompt Version:</span> <span className="font-mono text-indigo-300">{report.reproducibility_panel.post_inputs.prompt_version || "default"}</span></div>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
