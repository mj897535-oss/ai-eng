"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { EvidenceLens, AnnotationItem } from "@/components/evidence/EvidenceLens";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch, UserProfile } from "@/lib/api";

interface AssessmentReportData {
  assessment_id: string;
  assessment_type: string;
  status: string;
  transcript: string | null;
  word_count: number;
  is_visible_to_participant: boolean;
  banner_notice: string;
  rubric_version: string;
  prompt_version?: string | null;
  model_version: string;
  annotations: AnnotationItem[];
}

export default function AssessmentReportPage({ params }: { params: { id: string } }) {
  const assessmentId = params.id;
  const [data, setData] = useState<AssessmentReportData | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [releasing, setReleasing] = useState<boolean>(false);
  const [releaseSuccess, setReleaseSuccess] = useState<boolean>(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch user profile
      try {
        const u = await apiFetch<UserProfile>("/auth/me");
        setUser(u);
      } catch {
        // Fallback for standalone demo
      }

      // Fetch assessment report
      const report = await apiFetch<AssessmentReportData>(`/assessments/${assessmentId}/report`);
      setData(report);

      // Try fetching audio url
      try {
        const audioData = await apiFetch<{ audio_url: string }>(`/assessments/${assessmentId}/audio-url`);
        if (audioData?.audio_url) {
          setAudioUrl(audioData.audio_url);
        }
      } catch {
        // Audio URL might not be available or mock
      }
    } catch (err: any) {
      console.warn("Error fetching assessment report:", err);
      setError(err?.message || "Failed to load assessment report");
      
      // Fallback for preview / demo with golden fixture (Appendix A)
      setData({
        assessment_id: assessmentId,
        assessment_type: "pre_test",
        status: "analyzed",
        transcript: "He go to college every day by bus, but yesterday he walk because the bus was late.",
        word_count: 17,
        is_visible_to_participant: true,
        banner_notice: "Automated preliminary analysis for research purposes. All candidate errors are unverified until human review.",
        rubric_version: "v1.0-jam-phd",
        prompt_version: "v1.0-assessor",
        model_version: "mock-llm-v1",
        annotations: [
          {
            annotation_id: "ann-preview-1",
            start_char: 3,
            end_char: 5,
            start_time_ms: 600,
            end_time_ms: 1100,
            candidate_error: "go",
            suggested_correction: "goes",
            category_code: "SVA",
            explanation: "Subject 'He' requires third-person singular verb 'goes' in simple present habit.",
            confidence: 0.96,
            ai_status: "suggested",
            flag: "none",
            rubric_version: "v1.0-jam-phd",
            prompt_version: "v1.0-assessor",
            model_version: "mock-llm-v1",
          },
          {
            annotation_id: "ann-preview-2",
            start_char: 55,
            end_char: 59,
            start_time_ms: 4500,
            end_time_ms: 5000,
            candidate_error: "walk",
            suggested_correction: "walked",
            category_code: "TNS",
            explanation: "Past temporal marker 'yesterday' requires simple past 'walked'.",
            confidence: 0.94,
            ai_status: "suggested",
            flag: "none",
            rubric_version: "v1.0-jam-phd",
            prompt_version: "v1.0-assessor",
            model_version: "mock-llm-v1",
          },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRelease = async () => {
    setReleasing(true);
    try {
      await apiFetch(`/assessments/${assessmentId}/release`, {
        method: "POST",
      });
      setReleaseSuccess(true);
      if (data) {
        setData({
          ...data,
          is_visible_to_participant: true,
        });
      }
    } catch (err: any) {
      alert("Failed to release assessment: " + (err?.message || "Unknown error"));
    } finally {
      setReleasing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Loading Evidence Lens report...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center space-y-4">
          <h2 className="text-xl font-serif font-bold text-slate-900 dark:text-slate-100">Report Not Found</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {error || "The requested assessment report could not be found."}
          </p>
          <Link href="/dashboard">
            <Button variant="outline">Return to Dashboard</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const isResearcher = user ? user.role !== "participant" : true;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      {/* Top Header & Breadcrumbs */}
      <div className="max-w-6xl mx-auto mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <Link href="/dashboard" className="hover:underline">Dashboard</Link>
            <span>/</span>
            <Link href="/assessments" className="hover:underline">Assessments</Link>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-200 font-medium font-mono text-xs">{assessmentId.slice(0, 8)}...</span>
            <span>/</span>
            <span className="text-emerald-700 dark:text-emerald-400 font-semibold">Evidence Lens</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Assessment Evidence Lens
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1">
            Interactive syntactic deviation inspector (Signature Feature A). Audio-aligned word-level spans with transparent rubric justification.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Chip variant={data.is_visible_to_participant ? "success" : "warning"} size="sm">
            {data.is_visible_to_participant ? "Status: Released to Participant" : "Status: Blinded / Unreleased"}
          </Chip>

          {isResearcher && !data.is_visible_to_participant && (
            <Button
              size="sm"
              onClick={handleRelease}
              disabled={releasing}
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
            >
              {releasing ? "Releasing..." : "Release to Participant"}
            </Button>
          )}

          {releaseSuccess && (
            <span className="text-xs text-emerald-600 font-medium">Released!</span>
          )}
        </div>
      </div>

      {/* Main Evidence Lens Container */}
      <div className="max-w-6xl mx-auto">
        <EvidenceLens
          assessmentId={data.assessment_id}
          assessmentType={data.assessment_type}
          transcript={data.transcript || ""}
          wordCount={data.word_count}
          annotations={data.annotations}
          bannerNotice={data.banner_notice}
          isVisibleToParticipant={data.is_visible_to_participant}
          rubricVersion={data.rubric_version}
          promptVersion={data.prompt_version}
          modelVersion={data.model_version}
          audioPlaybackUrl={audioUrl}
          isResearcher={isResearcher}
          onReleaseResults={handleRelease}
        />
      </div>
    </div>
  );
}
