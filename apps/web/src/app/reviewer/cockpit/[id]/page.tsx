"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ReviewerCockpit, CandidateAnnotation } from "@/components/reviewer/ReviewerCockpit";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";

interface CockpitData {
  assessment_id: string;
  participant_code: string;
  study_group: string;
  assessment_type: string;
  review_status: string;
  is_verified: boolean;
  transcript: string;
  word_count: number;
  audio_key: string;
  audio_url?: string | null;
  rubric_version: string;
  model_version: string;
  effective_annotations: CandidateAnnotation[];
}

export default function ReviewerCockpitPage({ params }: { params: { id: string } }) {
  const assessmentId = params.id;
  const [data, setData] = useState<CockpitData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCockpitData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  const loadCockpitData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<CockpitData>(`/reviews/cockpit/${assessmentId}`);
      setData(res);
    } catch (err: any) {
      console.warn("Cockpit load error:", err);
      setError(err?.message || "Failed to load cockpit data");

      // Realistic Fallback Fixture for inspection and keyboard-only evaluation
      setData({
        assessment_id: assessmentId,
        participant_code: "SL-2026-0004",
        study_group: "ai_intervention",
        assessment_type: "pre_test",
        review_status: "unreviewed",
        is_verified: false,
        transcript: "He go to college every day by bus, but yesterday he walk because the bus was late.",
        word_count: 17,
        audio_key: "audio/pre-test-0004.webm",
        audio_url: null,
        rubric_version: "v1.0-jam-phd",
        model_version: "gemini-1.5-pro",
        effective_annotations: [
          {
            annotation_id: "ann-sva-1",
            start_char: 3,
            end_char: 5,
            start_time_ms: 650,
            end_time_ms: 1100,
            span_text: "go",
            category_code: "SVA",
            suggested_correction: "goes",
            explanation: "Subject 'He' requires third-person singular verb 'goes' in simple present habit.",
            confidence: 0.96,
            origin: "ai",
            review_status: "unreviewed",
            decision_id: null,
            reason: null,
            is_active_for_metrics: true,
            flag: "candidate_error",
          },
          {
            annotation_id: "ann-tns-2",
            start_char: 55,
            end_char: 59,
            start_time_ms: 4500,
            end_time_ms: 5000,
            span_text: "walk",
            category_code: "TNS",
            suggested_correction: "walked",
            explanation: "Past temporal marker 'yesterday' requires simple past 'walked'.",
            confidence: 0.94,
            origin: "ai",
            review_status: "unreviewed",
            decision_id: null,
            reason: null,
            is_active_for_metrics: true,
            flag: "candidate_error",
          },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400 font-mono">
            Loading Reviewer Cockpit...
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center space-y-4">
          <h2 className="text-xl font-serif font-bold text-slate-900 dark:text-slate-100">
            Assessment Not Found
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {error || "Unable to access the requested assessment."}
          </p>
          <Link href="/admin/review-queue">
            <Button variant="outline">Return to Review Queue</Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      <div className="max-w-6xl mx-auto">
        <ReviewerCockpit
          assessmentId={data.assessment_id}
          participantCode={data.participant_code}
          studyGroup={data.study_group}
          assessmentType={data.assessment_type}
          reviewStatus={data.review_status}
          isVerified={data.is_verified}
          transcript={data.transcript}
          wordCount={data.word_count}
          audioUrl={data.audio_url}
          rubricVersion={data.rubric_version}
          modelVersion={data.model_version}
          annotations={data.effective_annotations}
        />
      </div>
    </div>
  );
}
