"use client";

import Link from "next/link";
import {
  ShieldCheck,
  Brain,
  Layers,
  Database,
  ArrowLeft,
  CheckCircle2,
  Lock,
  Sparkles,
  BookOpen,
} from "lucide-react";

export default function AboutPage() {
  const categories = [
    { code: "TNS", name: "Tense and Aspect", desc: "Deviations in verb tense, continuous forms, or aspectual markers." },
    { code: "SVA", name: "Subject-Verb Agreement", desc: "Singular/plural mismatches between subject person and verb inflection." },
    { code: "WO", name: "Word Order", desc: "Syntactic inversion, clause placement, and question formulation order." },
    { code: "AUX", name: "Auxiliary Usage", desc: "Omission, substitution, or redundant insertion of auxiliary verbs (do/be/have)." },
    { code: "ART", name: "Article Usage", desc: "Definite (the), indefinite (a/an), or non-target zero article insertion." },
    { code: "PREP", name: "Preposition Choice", desc: "Non-standard preposition selection or omission in idiomatic and directional phrases." },
    { code: "PRO", name: "Pronoun Reference", desc: "Case, gender, number, or relative pronoun mismatch in complex clauses." },
    { code: "OTH", name: "Other / Uncertain", desc: "Regional Indian English syntactic features flagged for specialist reviewer validation." },
  ];

  const hintLadder = [
    { level: "L0", title: "Target Quote", desc: "The tutor highlights the exact learner utterance without providing the correction." },
    { level: "L1", title: "Guiding Question", desc: "A reflective question prompts the learner to notice the structural feature." },
    { level: "L2", title: "Grammar Rule Cue", desc: "A concise grammatical explanation reminds the learner of the syntactic rule." },
    { level: "L3", title: "Model Reveal & Transfer", desc: "The tutor provides the target reconstruction and immediately invites a transfer response." },
  ];

  return (
    <div className="flex-1 flex flex-col items-center px-4 py-12 sm:px-6 lg:px-8 max-w-5xl mx-auto w-full">
      <div className="w-full mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
      </div>

      <header className="text-center space-y-4 mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
          <ShieldCheck className="w-4 h-4" />
          <span>Research Protocol & Architecture Specification</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Study Protocol & System Design
        </h1>
        <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-600 dark:text-slate-300">
          Longitudinal Evaluation of Form-Focused AI Conversational Tutoring on Spoken English Syntactic Accuracy in Engineering Undergraduates.
        </p>
      </header>

      {/* Overview Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-12">
        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400">
            <Brain className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">AI-Powered Assessment</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Speech-to-text pipeline captures 1-minute spontaneous speech and applies an 8-category syntactic taxonomy with reviewer verification.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-950/60 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Layers className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">4-Level Hint Ladder</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Pedagogical scaffolding engine that adjusts assistance level dynamically based on learner self-correction attempts.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <Database className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Immutability & Integrity</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Strict PostgreSQL append-only triggers, pseudonymized research identifiers, and separate identity/research database schemas.
          </p>
        </div>
      </section>

      {/* 8 Syntactic Categories Taxonomy */}
      <section className="w-full mb-12 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Frozen Syntactic Taxonomy (v1.0-jam-phd)</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Standardized 8-category error taxonomy with strict operational definitions</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {categories.map((cat) => (
            <div key={cat.code} className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/60 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-900 dark:text-white text-sm">{cat.name}</span>
                <span className="text-xs px-2 py-0.5 font-mono font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 rounded">
                  {cat.code}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400">{cat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Hint Ladder Section */}
      <section className="w-full mb-12 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <Sparkles className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Conversational AI Hint Ladder (Signature Feature C)</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Minimal interventions maximizing learner self-correction</p>
          </div>
        </div>

        <div className="space-y-4">
          {hintLadder.map((hint) => (
            <div key={hint.level} className="flex gap-4 items-start p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-slate-700/60">
              <span className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm bg-indigo-600 text-white shrink-0">
                {hint.level}
              </span>
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">{hint.title}</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">{hint.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Security & Ethical Safeguards */}
      <section className="w-full mb-12 bg-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-lg">
        <div className="flex items-center gap-3 mb-6">
          <Lock className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-bold">Privacy-by-Design & Research Ethics (ASVS L2)</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-slate-300">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>PII strictly stored in <code>identity</code> schema; research audio & assessments in <code>research</code> schema.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>Append-only database triggers prevent mutation or deletion of audit logs and verification decisions.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>AI Provider Privacy Gate ensures zero data retention and zero training on participant speech samples.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>Automated de-identified research exports with cryptographic checksum verification and dynamic data dictionary.</span>
          </div>
        </div>
      </section>

      {/* Action CTA */}
      <div className="flex flex-col sm:flex-row gap-4 w-full justify-center max-w-md">
        <Link
          href="/login"
          className="flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors text-center"
        >
          Sign In to Portal
        </Link>
        <Link
          href="/onboarding"
          className="flex items-center justify-center px-6 py-3 border border-slate-300 dark:border-slate-700 text-base font-medium rounded-lg text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 shadow-sm transition-colors text-center"
        >
          Join Study Cohort
        </Link>
      </div>
    </div>
  );
}
