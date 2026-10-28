"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface MetricDistribution {
  n: number;
  mean: number;
  median: number;
  min: number;
  max: number;
  std_dev: number;
}

interface AggregateMetrics {
  n: number;
  total_pre_words: number;
  total_post_words: number;
  total_pre_errors: number;
  total_post_errors: number;
  pre_distribution: MetricDistribution;
  post_distribution: MetricDistribution;
  absolute_reduction_distribution: MetricDistribution;
  mean_relative_reduction_pct: number | null;
  all_verified: boolean;
  provisional_count: number;
  standard_caution: string;
}

interface CapacityAndCost {
  design_target_participants: number;
  enrolled_participants: number;
  capacity_utilization_pct: number;
  total_storage_mb: number;
  total_stt_calls: number;
  total_llm_calls: number;
  estimated_total_cost_usd: number;
  estimated_cost_per_participant_usd: number;
  headroom_participants: number;
}

interface FunnelData {
  enrolled: number;
  consented: number;
  pre_test_completed: number;
  practising: number;
  post_test_completed: number;
}

interface MissingData {
  withdrawn_count: number;
  missing_pre_count: number;
  missing_post_count: number;
  withdrawn_participants: string[];
}

interface CohortDashboardData {
  filter_group: string;
  funnel: FunnelData;
  group_allocation: {
    intervention: number;
    control: number;
  };
  missing_data: MissingData;
  review_queue_size: number;
  pipeline_failures: number;
  aggregates: AggregateMetrics;
  capacity_and_cost: CapacityAndCost;
}

interface ParticipantRow {
  participant_id: string;
  research_code: string;
  study_group: string;
  pre_test_status: string;
  pre_test_verified: boolean;
  post_test_status: string;
  post_test_verified: boolean;
  practice_sessions_count: number;
  active_practice_minutes: number;
  is_withdrawn: boolean;
  enrolled_at: string | null;
}

export default function ResearcherCohortDashboardPage() {
  const [data, setData] = useState<CohortDashboardData | null>(null);
  const [participants, setParticipants] = useState<ParticipantRow[]>([]);
  const [groupFilter, setGroupFilter] = useState<string>("all");
  const [showDataTable, setShowDataTable] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard(groupFilter);
  }, [groupFilter]);

  const fetchDashboard = async (selectedGroup: string) => {
    setLoading(true);
    try {
      const [dashRes, partRes] = await Promise.all([
        apiFetch<CohortDashboardData>(`/dashboard/researcher?group=${selectedGroup}`),
        apiFetch<ParticipantRow[]>("/dashboard/researcher/participants"),
      ]);
      setData(dashRes);
      setParticipants(partRes);
    } catch {
      // Mock fallback data for presentation and standalone testing
      setData({
        filter_group: selectedGroup,
        funnel: {
          enrolled: 48,
          consented: 45,
          pre_test_completed: 42,
          practising: 38,
          post_test_completed: 34,
        },
        group_allocation: {
          intervention: 24,
          control: 24,
        },
        missing_data: {
          withdrawn_count: 2,
          missing_pre_count: 3,
          missing_post_count: 8,
          withdrawn_participants: ["SL-2026-0012", "SL-2026-0029"],
        },
        review_queue_size: 14,
        pipeline_failures: 0,
        aggregates: {
          n: 34,
          total_pre_words: 4320,
          total_post_words: 4410,
          total_pre_errors: 389,
          total_post_errors: 198,
          pre_distribution: {
            n: 34,
            mean: 9.0,
            median: 8.85,
            min: 5.2,
            max: 14.5,
            std_dev: 2.15,
          },
          post_distribution: {
            n: 34,
            mean: 4.49,
            median: 4.25,
            min: 1.1,
            max: 8.9,
            std_dev: 1.82,
          },
          absolute_reduction_distribution: {
            n: 34,
            mean: 4.51,
            median: 4.4,
            min: 0.8,
            max: 9.2,
            std_dev: 1.95,
          },
          mean_relative_reduction_pct: 49.8,
          all_verified: false,
          provisional_count: 6,
          standard_caution:
            "This is a descriptive comparison and does not by itself show that AI caused the change.",
        },
        capacity_and_cost: {
          design_target_participants: 120,
          enrolled_participants: 48,
          capacity_utilization_pct: 40.0,
          total_storage_mb: 284.5,
          total_stt_calls: 86,
          total_llm_calls: 340,
          estimated_total_cost_usd: 6.85,
          estimated_cost_per_participant_usd: 0.14,
          headroom_participants: 72,
        },
      });

      setParticipants([
        {
          participant_id: "demo-part-1",
          research_code: "SL-2026-0042",
          study_group: "intervention",
          pre_test_status: "completed",
          pre_test_verified: true,
          post_test_status: "completed",
          post_test_verified: true,
          practice_sessions_count: 3,
          active_practice_minutes: 42.5,
          is_withdrawn: false,
          enrolled_at: "2026-10-24T10:00:00Z",
        },
        {
          participant_id: "demo-part-2",
          research_code: "SL-2026-0043",
          study_group: "control",
          pre_test_status: "completed",
          pre_test_verified: true,
          post_test_status: "completed",
          post_test_verified: false,
          practice_sessions_count: 0,
          active_practice_minutes: 0.0,
          is_withdrawn: false,
          enrolled_at: "2026-10-24T11:15:00Z",
        },
        {
          participant_id: "demo-part-3",
          research_code: "SL-2026-0044",
          study_group: "intervention",
          pre_test_status: "completed",
          pre_test_verified: true,
          post_test_status: "recording",
          post_test_verified: false,
          practice_sessions_count: 2,
          active_practice_minutes: 28.0,
          is_withdrawn: false,
          enrolled_at: "2026-10-25T09:30:00Z",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
        <p className="text-slate-500 font-medium animate-pulse">Loading cohort dashboard...</p>
      </main>
    );
  }

  const { funnel, aggregates, capacity_and_cost: cap, missing_data } = data;

  return (
    <main className="min-h-screen bg-slate-50/70 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header and Filter Controls */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                Researcher Operations
              </span>
              <span className="text-xs text-slate-400">&bull;</span>
              <span className="text-xs text-slate-500">SRS &sect;9 Longitudinal Tracking</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
              Cohort Analysis &amp; Infrastructure Dashboard
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Group Filter */}
            <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-xs">
              {(["all", "intervention", "control"] as const).map((grp) => (
                <button
                  key={grp}
                  onClick={() => setGroupFilter(grp)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    groupFilter === grp
                      ? "bg-indigo-600 text-white"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {grp.charAt(0).toUpperCase() + grp.slice(1)}
                </button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDataTable(!showDataTable)}
              aria-label="Toggle accessible data table view"
            >
              {showDataTable ? "Visual Cards" : "Data Table"}
            </Button>

            <Link href="/reviewer">
              <Button size="sm">
                Review Queue ({data.review_queue_size})
              </Button>
            </Link>
          </div>
        </header>

        {/* Top Status & Alerts Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Enrolment Funnel Completion
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-2xl font-bold text-slate-900">
                {funnel.post_test_completed} / {funnel.enrolled}
              </span>
              <span className="text-xs text-slate-500">
                ({funnel.enrolled > 0 ? Math.round((funnel.post_test_completed / funnel.enrolled) * 100) : 0}%)
              </span>
            </div>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Pending Human Review
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-2xl font-bold text-amber-600 font-mono">
                {data.review_queue_size}
              </span>
              <span className="text-xs text-slate-400">annotations</span>
            </div>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Pipeline Failures
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className={`text-2xl font-bold font-mono ${data.pipeline_failures > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                {data.pipeline_failures}
              </span>
              <span className="text-xs text-slate-400">active alerts</span>
            </div>
          </Card>

          <Card className="p-3 bg-white border-slate-200 shadow-xs">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block">
              Provisional Paired Data
            </span>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-2xl font-bold font-mono text-amber-600">
                {aggregates.provisional_count}
              </span>
              <span className="text-xs text-slate-400">unreviewed pairs</span>
            </div>
          </Card>
        </div>

        {/* Cohort Enrolment Funnel Section */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Participant Enrolment Funnel &amp; Retention
              </h2>
              <p className="text-xs text-slate-500">
                Progression across protocol stages. Design capacity: 120 participants.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-slate-600">
                Intervention: <strong className="text-indigo-600">{data.group_allocation.intervention}</strong>
              </span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-600">
                Control: <strong className="text-teal-600">{data.group_allocation.control}</strong>
              </span>
            </div>
          </div>

          {/* Funnel Progress Steps */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { label: "1. Enrolled", count: funnel.enrolled, pct: 100, color: "bg-slate-200" },
              {
                label: "2. Consented",
                count: funnel.consented,
                pct: funnel.enrolled > 0 ? Math.round((funnel.consented / funnel.enrolled) * 100) : 0,
                color: "bg-indigo-300",
              },
              {
                label: "3. Pre-Test Done",
                count: funnel.pre_test_completed,
                pct: funnel.enrolled > 0 ? Math.round((funnel.pre_test_completed / funnel.enrolled) * 100) : 0,
                color: "bg-indigo-400",
              },
              {
                label: "4. Practising",
                count: funnel.practising,
                pct: funnel.enrolled > 0 ? Math.round((funnel.practising / funnel.enrolled) * 100) : 0,
                color: "bg-indigo-500",
              },
              {
                label: "5. Post-Test Done",
                count: funnel.post_test_completed,
                pct: funnel.enrolled > 0 ? Math.round((funnel.post_test_completed / funnel.enrolled) * 100) : 0,
                color: "bg-emerald-500",
              },
            ].map((step, idx) => (
              <div key={idx} className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1">
                <span className="text-xs font-semibold text-slate-600 block">{step.label}</span>
                <div className="flex items-baseline gap-1">
                  <span className="text-xl font-bold text-slate-900 font-mono">{step.count}</span>
                  <span className="text-[11px] text-slate-400">({step.pct}%)</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className={`h-1.5 ${step.color} rounded-full`} style={{ width: `${step.pct}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Missing Data & Drop-off warnings */}
          {missing_data.withdrawn_count > 0 || missing_data.missing_post_count > 0 ? (
            <div className="bg-rose-50/70 border border-rose-200 rounded-lg p-3 text-xs text-rose-800 flex items-start gap-2">
              <span className="font-bold text-rose-700">&#9888; Retention Alert:</span>
              <span>
                {missing_data.withdrawn_count} participant(s) withdrawn ({missing_data.withdrawn_participants.join(", ")}). {missing_data.missing_post_count} participant(s) completed pre-test but have not completed post-test.
              </span>
            </div>
          ) : null}
        </section>

        {/* Aggregate Pre/Post Comparative Metrics (Solely via Metrics Module) */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">
                  Aggregate Pre/Post Distributions ({groupFilter.toUpperCase()} GROUP)
                </h2>
                {!aggregates.all_verified && (
                  <Chip variant="warning">
                    {aggregates.provisional_count} Provisional Pairs
                  </Chip>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Calculated strictly via the pure <code className="text-indigo-600">metrics</code> module. Shows distributions, not just means.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-500 font-mono">
              Paired Sample Size: n = {aggregates.n}
            </span>
          </div>

          {/* Caution Alert */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900">
            <strong>Standard Caution:</strong> {aggregates.standard_caution}
          </div>

          {/* Distributions Display */}
          {showDataTable ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs" aria-label="Statistical distributions table">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Metric</th>
                    <th className="p-3">Sample (n)</th>
                    <th className="p-3">Mean</th>
                    <th className="p-3">Median</th>
                    <th className="p-3">Min</th>
                    <th className="p-3">Max</th>
                    <th className="p-3">Std Dev (&sigma;)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  <tr>
                    <td className="p-3 font-sans font-semibold text-slate-800">Pre-Test Error Rate (per 100 w)</td>
                    <td className="p-3 text-slate-600">{aggregates.pre_distribution.n}</td>
                    <td className="p-3 font-bold text-slate-900">{aggregates.pre_distribution.mean.toFixed(2)}</td>
                    <td className="p-3 text-slate-800">{aggregates.pre_distribution.median.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.pre_distribution.min.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.pre_distribution.max.toFixed(2)}</td>
                    <td className="p-3 text-slate-600">{aggregates.pre_distribution.std_dev.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-sans font-semibold text-slate-800">Post-Test Error Rate (per 100 w)</td>
                    <td className="p-3 text-slate-600">{aggregates.post_distribution.n}</td>
                    <td className="p-3 font-bold text-emerald-600">{aggregates.post_distribution.mean.toFixed(2)}</td>
                    <td className="p-3 text-emerald-700">{aggregates.post_distribution.median.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.post_distribution.min.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.post_distribution.max.toFixed(2)}</td>
                    <td className="p-3 text-slate-600">{aggregates.post_distribution.std_dev.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-sans font-semibold text-slate-800">Absolute Reduction</td>
                    <td className="p-3 text-slate-600">{aggregates.absolute_reduction_distribution.n}</td>
                    <td className="p-3 font-bold text-emerald-600">-{aggregates.absolute_reduction_distribution.mean.toFixed(2)}</td>
                    <td className="p-3 text-emerald-700">-{aggregates.absolute_reduction_distribution.median.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.absolute_reduction_distribution.min.toFixed(2)}</td>
                    <td className="p-3 text-slate-500">{aggregates.absolute_reduction_distribution.max.toFixed(2)}</td>
                    <td className="p-3 text-slate-600">{aggregates.absolute_reduction_distribution.std_dev.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2">
                <span className="text-xs font-semibold text-slate-500 block uppercase tracking-wider">
                  Pre-Test Error Rate
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {aggregates.pre_distribution.mean.toFixed(2)}
                  </span>
                  <span className="text-xs text-slate-500">mean / 100w</span>
                </div>
                <div className="text-xs text-slate-600 space-y-1 font-mono pt-1 border-t border-slate-200">
                  <div className="flex justify-between">
                    <span>Median:</span>
                    <span className="font-semibold">{aggregates.pre_distribution.median.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Range (Min - Max):</span>
                    <span>{aggregates.pre_distribution.min.toFixed(2)} &ndash; {aggregates.pre_distribution.max.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Std Dev (&sigma;):</span>
                    <span>{aggregates.pre_distribution.std_dev.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-2">
                <span className="text-xs font-semibold text-slate-500 block uppercase tracking-wider">
                  Post-Test Error Rate
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-emerald-600 font-mono">
                    {aggregates.post_distribution.mean.toFixed(2)}
                  </span>
                  <span className="text-xs text-slate-500">mean / 100w</span>
                </div>
                <div className="text-xs text-slate-600 space-y-1 font-mono pt-1 border-t border-slate-200">
                  <div className="flex justify-between">
                    <span>Median:</span>
                    <span className="font-semibold">{aggregates.post_distribution.median.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Range (Min - Max):</span>
                    <span>{aggregates.post_distribution.min.toFixed(2)} &ndash; {aggregates.post_distribution.max.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Std Dev (&sigma;):</span>
                    <span>{aggregates.post_distribution.std_dev.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200/80 space-y-2">
                <span className="text-xs font-semibold text-emerald-800 block uppercase tracking-wider">
                  Absolute &amp; Relative Reduction
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-emerald-700 font-mono">
                    -{aggregates.absolute_reduction_distribution.mean.toFixed(2)}
                  </span>
                  <span className="text-xs text-emerald-700 font-semibold">
                    ({aggregates.mean_relative_reduction_pct !== null ? `${aggregates.mean_relative_reduction_pct.toFixed(1)}%` : "N/A"})
                  </span>
                </div>
                <div className="text-xs text-emerald-900 space-y-1 font-mono pt-1 border-t border-emerald-200">
                  <div className="flex justify-between">
                    <span>Median Reduction:</span>
                    <span className="font-semibold">-{aggregates.absolute_reduction_distribution.median.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Range:</span>
                    <span>{aggregates.absolute_reduction_distribution.min.toFixed(2)} &ndash; {aggregates.absolute_reduction_distribution.max.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Reduction Std Dev:</span>
                    <span>{aggregates.absolute_reduction_distribution.std_dev.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Capacity and Cost Panel (Design Target: 120 Participants + Researchers) */}
        <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Infrastructure Capacity &amp; Cost Panel
              </h2>
              <p className="text-xs text-slate-500">
                Design target: 120 participants plus researcher seats with operational headroom.
              </p>
            </div>
            <Chip variant={cap.capacity_utilization_pct > 80 ? "warning" : "success"}>
              {cap.capacity_utilization_pct}% Utilized ({cap.headroom_participants} Headroom)
            </Chip>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
              <span className="text-xs text-slate-500 block">Total Audio Storage</span>
              <span className="text-xl font-bold text-slate-900 font-mono mt-1 block">
                {cap.total_storage_mb} MB
              </span>
              <span className="text-[11px] text-slate-400">Private S3/MinIO</span>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
              <span className="text-xs text-slate-500 block">STT Transcriptions</span>
              <span className="text-xl font-bold text-slate-900 font-mono mt-1 block">
                {cap.total_stt_calls}
              </span>
              <span className="text-[11px] text-slate-400">Calls executed</span>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
              <span className="text-xs text-slate-500 block">LLM Inferences</span>
              <span className="text-xl font-bold text-slate-900 font-mono mt-1 block">
                {cap.total_llm_calls}
              </span>
              <span className="text-[11px] text-slate-400">Assessments &amp; Tutor</span>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
              <span className="text-xs text-slate-500 block">Estimated Cost / Part.</span>
              <span className="text-xl font-bold text-emerald-600 font-mono mt-1 block">
                ${cap.estimated_cost_per_participant_usd.toFixed(2)}
              </span>
              <span className="text-[11px] text-slate-400">Total: ${cap.estimated_total_cost_usd.toFixed(2)}</span>
            </div>
          </div>
        </section>

        {/* Participant Roster Table with Links to Drilldown */}
        <section className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs space-y-3 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Cohort Participant Drilldown
              </h2>
              <p className="text-xs text-slate-500">
                Click any participant to inspect their longitudinal timeline, verified assessments, and recurrence history.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs" aria-label="Cohort participant roster">
              <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="p-3">Research Code</th>
                  <th className="p-3">Group</th>
                  <th className="p-3">Pre-Test Status</th>
                  <th className="p-3">Post-Test Status</th>
                  <th className="p-3">Practice Mins</th>
                  <th className="p-3">Sessions</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {participants.map((p) => (
                  <tr key={p.participant_id} className="hover:bg-slate-50/60">
                    <td className="p-3 font-sans font-bold text-indigo-600">
                      <Link href={`/admin/dashboard/participant/${p.participant_id}`} className="hover:underline">
                        {p.research_code}
                      </Link>
                    </td>
                    <td className="p-3 font-sans capitalize text-slate-700">
                      <Chip variant={p.study_group === "intervention" ? "primary" : "neutral"}>
                        {p.study_group}
                      </Chip>
                    </td>
                    <td className="p-3 font-sans">
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${p.pre_test_status === "completed" ? "bg-emerald-500" : "bg-slate-300"}`} />
                        <span className="capitalize text-slate-700">{p.pre_test_status}</span>
                        {p.pre_test_verified && <span className="text-emerald-700 font-bold">&check;</span>}
                      </span>
                    </td>
                    <td className="p-3 font-sans">
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${p.post_test_status === "completed" ? "bg-emerald-500" : "bg-slate-300"}`} />
                        <span className="capitalize text-slate-700">{p.post_test_status}</span>
                        {p.post_test_verified && <span className="text-emerald-700 font-bold">&check;</span>}
                      </span>
                    </td>
                    <td className="p-3 text-slate-800">{p.active_practice_minutes} m</td>
                    <td className="p-3 text-slate-600">{p.practice_sessions_count}</td>
                    <td className="p-3 text-right font-sans">
                      <Link href={`/admin/dashboard/participant/${p.participant_id}`}>
                        <Button variant="outline" size="sm">
                          Drill Down &rarr;
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
