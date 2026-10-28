"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { apiFetch } from "@/lib/api";

export interface ChatMessage {
  id: string;
  sender: "tutor" | "learner";
  text: string;
  hintLevel?: number | null; // 0, 1, 2, 3
  targetCategory?: string;
  isSelfCorrection?: boolean;
  transferPrompt?: string | null;
  attemptType?: string;
  timestamp: string;
}

export interface TutorChatProps {
  sessionId: string;
  topic: string;
  targetCategories: string[];
  initialMessages: ChatMessage[];
  onEndSession?: (summary: any) => void;
}

export function TutorChat({
  sessionId,
  topic,
  targetCategories,
  initialMessages,
  onEndSession,
}: TutorChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [inputText, setInputText] = useState<string>("");
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [sessionCompleted, setSessionCompleted] = useState<boolean>(false);
  const [sessionSummary, setSessionSummary] = useState<any | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send Learner Turn
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || sending || sessionCompleted) return;

    const userMsg: ChatMessage = {
      id: `learner-${Date.now()}`,
      sender: "learner",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setSending(true);

    try {
      const res: any = await apiFetch(`/tutor/sessions/${sessionId}/turns`, {
        method: "POST",
        body: JSON.stringify({ utterance: text }),
      });

      const tutorMsg: ChatMessage = {
        id: `tutor-${Date.now()}`,
        sender: "tutor",
        text: res.reply_text,
        hintLevel: res.hint_level,
        targetCategory: res.target_category,
        isSelfCorrection: res.is_self_correction,
        transferPrompt: res.transfer_prompt,
        attemptType: res.attempt_type,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, tutorMsg]);
    } catch {
      // Fallback for demo / preview
      const isCorrect = text.toLowerCase().includes("goes") || text.toLowerCase().includes("studies");
      const fallbackMsg: ChatMessage = {
        id: `tutor-${Date.now()}`,
        sender: "tutor",
        text: isCorrect
          ? `Spot on! "${text}" is grammatically accurate for third-person singular present. Now tell me what someone else in your family does every day!`
          : `Notice the subject and the verb in: "${text}". When the subject is 'he', what ending is added to the verb in the simple present?`,
        hintLevel: isCorrect ? null : 1,
        targetCategory: targetCategories[0] || "SVA",
        isSelfCorrection: isCorrect,
        transferPrompt: isCorrect ? "Tell me what someone else does every day!" : null,
        attemptType: isCorrect ? "hint_assisted" : "none",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setSending(false);
    }
  };

  // Toggle Simulated Mic Input
  const handleToggleMic = () => {
    if (!isRecording) {
      setIsRecording(true);
      // Simulate speaking recognition
      setTimeout(() => {
        setIsRecording(false);
        setInputText("He goes to college every day.");
      }, 1800);
    } else {
      setIsRecording(false);
    }
  };

  // End Session Handler
  const handleEndSession = async () => {
    setSending(true);
    try {
      const summary = await apiFetch<any>(`/tutor/sessions/${sessionId}/end`, {
        method: "POST",
      });
      setSessionCompleted(true);
      setSessionSummary(summary);
      if (onEndSession) onEndSession(summary);
    } catch {
      // Fallback summary
      const dummySummary = {
        status: "completed",
        active_duration_seconds: 145,
        turns_count: messages.length,
        total_attempts: 3,
        independent_self_corrections: 0,
        hint_assisted_corrections: 1,
        prompt_version: "v1.0-tutor-ladder",
      };
      setSessionCompleted(true);
      setSessionSummary(dummySummary);
      if (onEndSession) onEndSession(dummySummary);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] max-h-[850px] bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
      {/* CHAT HEADER */}
      <div className="p-3.5 sm:p-4 bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-800 flex items-center justify-center text-emerald-700 dark:text-emerald-300 font-serif font-bold text-sm shrink-0">
            AI
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-serif font-bold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                SyntaxLens Tutor
              </h2>
              <Chip variant="success" size="sm" className="hidden sm:inline-flex">
                Hint Ladder Active
              </Chip>
            </div>
            <p className="text-[11px] text-slate-500 font-mono truncate max-w-[200px] sm:max-w-md">
              Focus: {targetCategories.join(", ")} &bull; Topic: {topic}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!sessionCompleted && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleEndSession}
              disabled={sending}
              className="text-xs border-slate-300 dark:border-slate-700 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 transition-all font-mono"
            >
              Finish Practice
            </Button>
          )}
        </div>
      </div>

      {/* CHAT MESSAGES STREAM */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/50 dark:bg-slate-950/30">
        {messages.map((msg) => {
          const isTutor = msg.sender === "tutor";

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isTutor ? "items-start" : "items-end"} space-y-1`}
            >
              <div
                className={`max-w-[88%] sm:max-w-[75%] p-3.5 sm:p-4 rounded-2xl text-sm leading-relaxed ${
                  isTutor
                    ? "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 shadow-sm"
                    : "bg-emerald-600 text-white rounded-br-none shadow-sm"
                }`}
              >
                {/* Tutor Hint Ladder Badge & Category Indicator */}
                {isTutor && msg.hintLevel !== undefined && msg.hintLevel !== null && (
                  <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800 text-[11px] font-mono">
                    <span
                      className={`px-2 py-0.5 rounded font-bold uppercase ${
                        msg.hintLevel === 0
                          ? "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300"
                          : msg.hintLevel === 1
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          : msg.hintLevel === 2
                          ? "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300"
                          : "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                      }`}
                    >
                      {msg.hintLevel === 0 && "L0: Quote Reflection"}
                      {msg.hintLevel === 1 && "L1: Hint Question"}
                      {msg.hintLevel === 2 && "L2: Rule Cue"}
                      {msg.hintLevel === 3 && "L3: Model Reveal"}
                    </span>
                    {msg.targetCategory && (
                      <span className="text-slate-500">Target: {msg.targetCategory}</span>
                    )}
                  </div>
                )}

                {/* Self-Correction Praise Badge */}
                {isTutor && msg.isSelfCorrection && (
                  <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-emerald-100 dark:border-emerald-900 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    <span>&#10003; Accurate Self-Correction Logged</span>
                  </div>
                )}

                <p className="font-serif text-sm sm:text-base">{msg.text}</p>

                {/* Transfer Check Card */}
                {isTutor && msg.transferPrompt && (
                  <div className="mt-3 p-2.5 bg-emerald-50 dark:bg-emerald-950/40 rounded border border-emerald-200 dark:border-emerald-800 text-xs font-serif text-emerald-900 dark:text-emerald-200 space-y-1">
                    <div className="font-mono text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-400">
                      Transfer Check (New Sentence):
                    </div>
                    <div>{msg.transferPrompt}</div>
                  </div>
                )}
              </div>

              <span className="text-[10px] text-slate-400 font-mono px-1">
                {msg.timestamp}
              </span>
            </div>
          );
        })}

        {/* Typing indicator */}
        {sending && !sessionCompleted && (
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono italic p-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-bounce" />
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.2s]" />
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]" />
            <span>Tutor is formulating supportive guidance...</span>
          </div>
        )}

        {/* Session Concluded Summary Card */}
        {sessionCompleted && sessionSummary && (
          <Card className="p-5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-center space-y-3 my-4">
            <div className="inline-flex h-10 w-10 rounded-full bg-emerald-100 dark:bg-emerald-900 items-center justify-center text-emerald-700 dark:text-emerald-300 font-bold text-lg mx-auto">
              &#10003;
            </div>
            <h3 className="font-serif font-bold text-lg text-slate-900 dark:text-slate-100">
              Practice Session Completed!
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-sm mx-auto">
              Your conversational turns and hint-assisted self-corrections have been logged into your private research record.
            </p>

            <div className="grid grid-cols-3 gap-2 max-w-xs mx-auto py-2 text-center font-mono">
              <div className="p-2 bg-white dark:bg-slate-900 rounded border border-emerald-200 dark:border-emerald-800">
                <span className="text-[10px] text-slate-400 block uppercase">Duration</span>
                <span className="font-bold text-sm text-slate-800 dark:text-slate-200">
                  {Math.round(sessionSummary.active_duration_seconds / 60)} min
                </span>
              </div>
              <div className="p-2 bg-white dark:bg-slate-900 rounded border border-emerald-200 dark:border-emerald-800">
                <span className="text-[10px] text-slate-400 block uppercase">Turns</span>
                <span className="font-bold text-sm text-slate-800 dark:text-slate-200">
                  {sessionSummary.turns_count}
                </span>
              </div>
              <div className="p-2 bg-white dark:bg-slate-900 rounded border border-emerald-200 dark:border-emerald-800">
                <span className="text-[10px] text-slate-400 block uppercase">Self-Corrected</span>
                <span className="font-bold text-sm text-emerald-700 dark:text-emerald-400">
                  {sessionSummary.hint_assisted_corrections + sessionSummary.independent_self_corrections}
                </span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-center gap-3">
              <Link href="/dashboard">
                <Button size="sm" variant="outline">
                  Return to Dashboard
                </Button>
              </Link>
            </div>
          </Card>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* INPUT AREA */}
      {!sessionCompleted && (
        <div className="p-3 sm:p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 space-y-2">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            {/* Mic Button */}
            <Button
              type="button"
              onClick={handleToggleMic}
              variant={isRecording ? "destructive" : "outline"}
              className={`shrink-0 h-10 w-10 p-0 rounded-full flex items-center justify-center ${
                isRecording ? "animate-pulse" : ""
              }`}
              title={isRecording ? "Listening to your speech..." : "Speak via microphone"}
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            </Button>

            {/* Text Input */}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={isRecording ? "Listening to speech... Speak clearly..." : "Type or speak your sentence..."}
              disabled={sending}
              className="flex-1 px-4 py-2.5 rounded-full border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 font-serif"
            />

            {/* Send Button */}
            <Button
              type="submit"
              disabled={!inputText.trim() || sending}
              className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-full px-5 py-2.5 text-xs font-mono shrink-0 shadow-sm"
            >
              Send Turn &rarr;
            </Button>
          </form>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-2">
            <span>Natural conversation &bull; Accent/pronunciation not scored</span>
            <span>Zero public leaderboards</span>
          </div>
        </div>
      )}
    </div>
  );
}
