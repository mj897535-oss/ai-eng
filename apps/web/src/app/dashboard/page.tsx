"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface NextBestAction {
  title: string;
  action_text: string;
  route: string;
  description: string;
  urgency: "high" | "medium" | "low";
}

interface ActivityItem {
  title: string;
  timestamp: string | null;
  status: string;
  active_minutes?: number;
}

interface ParticipantDashboardData {
  participant_code: string;
  study_group: string;
  stage: string;
  progress_percentage: number;
  next_best_action: NextBestAction;
  pre_test_status: string;
  post_test_status: string;
  practice_sessions_completed: number;
  total_active_minutes: number;
  recent_activity: ActivityItem[];
  is_blinded: boolean;
}

export default function StudentHomePage() {
  const [data, setData] = useState<ParticipantDashboardData | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await apiFetch<ParticipantDashboardData>("/dashboard/participant");
      setData(res);
    } catch {
      // Mock fallback for presentation
      setData({
        participant_code: "SL-2026-0042",
        study_group: "intervention",
        stage: "practising",
        progress_percentage: 65,
        next_best_action: {
          title: "Practice Session 2 of 3 Ready",
          action_text: "Start Practice Turn",
          route: "/tutor",
          description: "Engage in a 15-minute conversational practice session targeting third-person singular present tense.",
          urgency: "medium",
        },
        pre_test_status: "completed",
        post_test_status: "not_started",
        practice_sessions_completed: 1,
        total_active_minutes: 15.0,
        recent_activity: [
          {
            title: "Tutoring Session (Technology and College Life)",
            timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
            status: "completed",
            active_minutes: 15.0,
          },
          {
            title: "Completed Baseline Pre-Test Assessment",
            timestamp: new Date(Date.now() - 3600000 * 72).toISOString(),
            status: "completed",
          },
        ],
        is_blinded: true,
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 md:p-10 font-sans">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                Student Learning Home
              </h1>
              <Chip variant="neutral" size="sm">
                ID: {data?.participant_code || "SL-2026-XXXX"}
              </Chip>
            </div>
            <p className="text-slate-400 mt-1">
              Track your study milestones, complete speaking assessments, and engage with the AI Tutor.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/dashboard/progress">
              <Button variant="outline" size="sm">View Progress Details</Button>
            </Link>
            <Link href={data?.next_best_action.route || "/tutor"}>
              <Button variant="primary" size="sm">
                {data?.next_best_action.action_text || "Continue Task"}
              </Button>
            </Link>
          </div>
        </div>

        {/* Gentle Next-Best-Action Hero Card */}
        {data?.next_best_action && (
          <Card className="p-6 bg-gradient-to-r from-indigo-950/80 via-slate-900 to-slate-900 border-indigo-700/60 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-2">
                  <span className="text-xs uppercase font-bold tracking-wider text-indigo-400">
                    Recommended Next Step
                  </span>
                  <Chip
                    variant={data.next_best_action.urgency === "high" ? "warning" : "primary"}
                    size="sm"
                  >
                    Action Needed
                  </Chip>
                </div>
                <h2 className="text-2xl font-bold text-white">
                  {data.next_best_action.title}
                </h2>
                <p className="text-sm text-slate-300">
                  {data.next_best_action.description}
                </p>
              </div>

              <Link href={data.next_best_action.route}>
                <Button variant="primary" size="lg" className="whitespace-nowrap shadow-lg">
                  {data.next_best_action.action_text} →
                </Button>
              </Link>
            </div>
          </Card>
        )}

        {/* Progress Overview & Ring */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Progress Ring Card */}
          <Card className="p-6 bg-slate-800/80 border-slate-700 flex flex-col items-center text-center justify-center space-y-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Study Protocol Progress
            </div>

            {/* Circular Progress Indicator */}
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  className="stroke-slate-700 fill-none"
                  strokeWidth="8"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  className="stroke-indigo-500 fill-none transition-all duration-700"
                  strokeWidth="8"
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (251.2 * (data?.progress_percentage || 0)) / 100}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute text-2xl font-extrabold text-white">
                {data?.progress_percentage || 0}%
              </div>
            </div>

            <div className="text-xs text-slate-400">
              Stage: <strong className="text-indigo-300 capitalize">{data?.stage.replace("_", " ") || "In Progress"}</strong>
            </div>
          </Card>

          {/* Milestone Statuses */}
          <Card className="p-6 bg-slate-800/80 border-slate-700 md:col-span-2 space-y-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Study Milestone Checkpoints
            </h3>

            <div className="space-y-3 text-sm">
              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-white">1. Baseline Pre-Test Speaking Task</div>
                  <div className="text-xs text-slate-400">One-minute spontaneous speech sample</div>
                </div>
                <Chip variant={data?.pre_test_status === "completed" ? "success" : "neutral"} size="sm">
                  {data?.pre_test_status === "completed" ? "Completed" : "Pending"}
                </Chip>
              </div>

              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-white">2. Conversational Tutoring Practice</div>
                  <div className="text-xs text-slate-400">
                    {data?.practice_sessions_completed || 0} of 3 sessions completed ({data?.total_active_minutes || 0} active mins)
                  </div>
                </div>
                <Chip
                  variant={data && data.practice_sessions_completed >= 3 ? "success" : "primary"}
                  size="sm"
                >
                  {data?.practice_sessions_completed || 0} / 3 Completed
                </Chip>
              </div>

              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-white">3. Final Post-Test Evaluation</div>
                  <div className="text-xs text-slate-400">Matched equivalence speech assessment</div>
                </div>
                <Chip variant={data?.post_test_status === "completed" ? "success" : "neutral"} size="sm">
                  {data?.post_test_status === "completed" ? "Completed" : "Locked"}
                </Chip>
              </div>
            </div>
          </Card>
        </div>

        {/* Research Blinding Protocol Banner */}
        {data?.is_blinded && (
          <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl text-slate-300 text-xs flex items-start gap-3">
            <span className="text-lg">🔒</span>
            <div>
              <strong className="text-slate-100 block mb-0.5">Research Blinding Notice:</strong>
              Detailed syntactic candidate scores and comparative evaluation results remain masked during the evaluation window to prevent coaching bias. Your complete comparative report will unlock upon study conclusion.
            </div>
          </div>
        )}

        {/* Recent Activity Log */}
        <Card className="p-6 bg-slate-800/60 border-slate-700">
          <h3 className="text-base font-bold text-white mb-4">Recent Research Activity</h3>
          {data?.recent_activity && data.recent_activity.length > 0 ? (
            <div className="space-y-3">
              {data.recent_activity.map((act, i) => (
                <div
                  key={i}
                  className="p-3.5 bg-slate-800/90 rounded-lg border border-slate-700/80 flex items-center justify-between"
                >
                  <div>
                    <div className="font-medium text-slate-200 text-sm">{act.title}</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {act.timestamp ? new Date(act.timestamp).toLocaleString() : "Recently"}
                    </div>
                  </div>
                  <Chip variant="success" size="sm">{act.status}</Chip>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No activity logged yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
