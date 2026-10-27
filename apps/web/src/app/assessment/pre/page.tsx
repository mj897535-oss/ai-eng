"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AudioRecorder } from "@/components/recorder/AudioRecorder";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface TaskInfo {
  task_id: string;
  title: string;
  prompt_text: string;
  prep_time_seconds: number;
  duration_seconds: number;
}

export default function PreTestAssessmentPage() {
  const [task, setTask] = useState<TaskInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTask();
  }, []);

  const fetchTask = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<any>("/api/v1/assessments/pre/presigned-url", {
        method: "POST",
        body: JSON.stringify({ codec: "audio/webm" }),
      });
      setTask(data.task);
    } catch (err: any) {
      console.warn("Pre-test task load:", err);
      setError(err?.message || "Failed to load pre-test task");
      // Fallback for preview or seed display
      setTask({
        task_id: "t1-preview",
        title: "A Memorable Journey or Trip",
        prompt_text: "Describe a memorable journey or trip you took in the past. Talk about where you went, how you travelled, and why this experience was special to you.",
        prep_time_seconds: 30,
        duration_seconds: 60,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      {/* Top Header */}
      <div className="max-w-4xl mx-auto mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Link href="/dashboard" className="hover:underline">Dashboard</Link>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-200 font-medium">Pre-Test Assessment</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Baseline Spoken English Assessment
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
            Official baseline recording. Please speak naturally in full sentences. Strictly blinded: no AI hints or scores will be displayed during this assessment.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Chip variant="primary" size="sm">Condition: Blinded Assessment</Chip>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500">
            Loading assigned assessment topic...
          </div>
        ) : task ? (
          <AudioRecorder
            assessmentType="pre"
            taskId={task.task_id}
            topicTitle={task.title}
            promptText={task.prompt_text}
            prepTimeSeconds={task.prep_time_seconds}
            durationSeconds={task.duration_seconds}
            maxRerecords={2}
          />
        ) : (
          <Card className="p-8 text-center text-rose-600">
            {error || "Could not load assigned pre-test topic."}
          </Card>
        )}
      </div>
    </div>
  );
}
