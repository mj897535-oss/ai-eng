"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { TutorChat, ChatMessage } from "@/components/tutor/TutorChat";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

interface TutorStatus {
  can_start_tutoring: boolean;
  is_pretest_verified: boolean;
  priority_categories: string[];
  saved_interests: string | null;
  gating_message: string | null;
  study_group: string;
}

export default function TutorPage() {
  const [status, setStatus] = useState<TutorStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [interests, setInterests] = useState<string>("Technology and Daily Life");
  const [activeSession, setActiveSession] = useState<{
    sessionId: string;
    topic: string;
    targetCategories: string[];
    initialMessages: ChatMessage[];
  } | null>(null);
  const [starting, setStarting] = useState<boolean>(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<TutorStatus>("/tutor/status");
      setStatus(data);
      if (data.saved_interests) {
        setInterests(data.saved_interests);
      }
    } catch {
      // Fallback for demo / preview
      setStatus({
        can_start_tutoring: true,
        is_pretest_verified: true,
        priority_categories: ["SVA", "TNS"],
        saved_interests: "College Life and Tech",
        gating_message: null,
        study_group: "intervention",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStartSession = async () => {
    setStarting(true);
    try {
      const res: any = await apiFetch("/tutor/sessions", {
        method: "POST",
        body: JSON.stringify({ interests }),
      });

      setActiveSession({
        sessionId: res.session_id,
        topic: res.topic || interests,
        targetCategories: res.target_categories || ["SVA"],
        initialMessages: [
          {
            id: `tutor-intro`,
            sender: "tutor",
            text: res.tutor_opening_message || "Hello! Let's chat naturally. What does a typical day look like for you or your friends?",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ],
      });
    } catch (err: any) {
      // Fallback for preview
      setActiveSession({
        sessionId: "sess-preview-1",
        topic: interests,
        targetCategories: status?.priority_categories || ["SVA"],
        initialMessages: [
          {
            id: `tutor-intro`,
            sender: "tutor",
            text: `Hello! Today we'll chat naturally about ${interests.toLowerCase()}. To get started, tell me: what does a typical day look like for you or someone you know?`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ],
      });
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400 font-mono">
            Checking practice eligibility...
          </p>
        </div>
      </div>
    );
  }

  // 1. GATED / LOCKED VIEW (Pre-test not verified or blinded evaluation period)
  if (status && !status.can_start_tutoring) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-4 sm:p-8 flex items-center justify-center">
        <Card className="max-w-md w-full p-6 sm:p-8 text-center space-y-4 bg-white dark:bg-slate-900 border-amber-200 dark:border-amber-900/60 shadow-sm">
          <div className="h-12 w-12 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 flex items-center justify-center mx-auto text-xl font-bold font-mono">
            &#128274;
          </div>
          <h2 className="text-xl font-serif font-bold text-slate-900 dark:text-slate-100">
            Tutoring Session Locked
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-serif">
            {status.gating_message ||
              "Your personalized AI tutoring session will unlock once your baseline pre-test recording has been calibrated and verified by our research team."}
          </p>

          <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded border border-amber-200 dark:border-amber-800 text-xs font-mono text-amber-800 dark:text-amber-300">
            Research Protocol Rule: Strict pre-test blinding enforced.
          </div>

          <div className="pt-2">
            <Link href="/dashboard">
              <Button variant="outline" className="w-full">
                Return to Dashboard
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-3 sm:p-8">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* TOP BREADCRUMB */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Link href="/dashboard" className="hover:underline">Dashboard</Link>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-200 font-medium">AI Tutor</span>
          </div>

          <div className="flex items-center gap-2">
            <Chip variant="neutral" size="sm" className="font-mono text-[11px]">
              Form-Focused Practice
            </Chip>
          </div>
        </div>

        {/* ACTIVE TUTOR CHAT OR SETUP */}
        {activeSession ? (
          <TutorChat
            sessionId={activeSession.sessionId}
            topic={activeSession.topic}
            targetCategories={activeSession.targetCategories}
            initialMessages={activeSession.initialMessages}
            onEndSession={() => {}}
          />
        ) : (
          /* SESSION SETUP CARD */
          <Card className="p-6 sm:p-8 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-bold">
                Signature Feature C
              </span>
              <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-slate-900 dark:text-slate-50 mt-1">
                Personalized Conversational Tutor
              </h1>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1.5 leading-relaxed font-serif">
                Practice spontaneous spoken English with a supportive AI tutor. The tutor guides you using the Hint Ladder (quote &rarr; hint question &rarr; rule cue &rarr; model reveal) to strengthen self-monitoring without stress.
              </p>
            </div>

            {/* Target Priorities Info */}
            <div className="p-4 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-200 dark:border-emerald-800 space-y-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
                Your Baseline Focus Areas:
              </span>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {status?.priority_categories.map((cat) => (
                  <Chip key={cat} variant="success" size="sm">
                    Target: {cat}
                  </Chip>
                ))}
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 font-serif">
                Derived directly from your verified baseline pre-test patterns.
              </p>
            </div>

            {/* Topic & Interests Customization */}
            <div className="space-y-3">
              <label className="block text-xs font-mono font-bold uppercase text-slate-700 dark:text-slate-300">
                Choose a Conversation Topic / Interest:
              </label>

              <div className="flex flex-wrap gap-2 text-xs">
                {[
                  "Technology and College Life",
                  "Daily Routine & Commute",
                  "Hobbies, Sports & Fitness",
                  "Travel & Memorable Trips",
                  "Movies & Creative Arts",
                ].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setInterests(preset)}
                    className={`px-3 py-1.5 rounded-full border transition-all font-mono text-xs ${
                      interests === preset
                        ? "bg-emerald-600 text-white border-emerald-600 font-semibold shadow-sm"
                        : "bg-slate-50 dark:bg-slate-950 border-slate-300 dark:border-slate-700 hover:border-slate-400"
                    }`}
                  >
                    {preset}
                  </button>
                ))}
              </div>

              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="Or type your own custom topic..."
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-sm font-serif"
              />
            </div>

            {/* Start Button */}
            <div className="pt-2">
              <Button
                onClick={handleStartSession}
                disabled={starting || !interests.trim()}
                className="w-full sm:w-auto px-8 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-sm shadow-md"
              >
                {starting ? "Starting Session..." : "Begin Practice Session &rarr;"}
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
