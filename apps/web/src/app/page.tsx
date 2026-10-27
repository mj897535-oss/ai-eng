import Link from "next/link";
import { ShieldCheck, Award, BookOpen, BarChart3 } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex-1 flex flex-col justify-center items-center px-4 py-12 sm:px-6 lg:px-8 max-w-5xl mx-auto w-full">
      <header className="text-center space-y-4 mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
          <ShieldCheck className="w-4 h-4" />
          <span>PhD Research Project • Cohort Protocol v1.0</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          SyntaxLens
        </h1>
        <p className="max-w-2xl mx-auto text-lg text-slate-600 dark:text-slate-300">
          Research-grade spoken English syntactic assessment and personalized tutoring.
        </p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-12">
        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <Award className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Standardized JAM Tasks</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            One-minute spontaneous speech tasks with faithful transcription and timestamped syntactic evidence.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <BookOpen className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Hint Ladder Tutor</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Structured scaffolding through quotes, hints, and rule cues, followed by transfer practice.
          </p>
        </div>

        <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <BarChart3 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Reproducible Metrics</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Transparent error rates per 100 words with verifiable denominators and audit integrity.
          </p>
        </div>
      </section>

      <div className="flex flex-col sm:flex-row gap-4 w-full justify-center max-w-md">
        <Link
          href="/login"
          className="flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Sign In to Portal
        </Link>
        <Link
          href="/about"
          className="flex items-center justify-center px-6 py-3 border border-slate-300 dark:border-slate-700 text-base font-medium rounded-lg text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Study Protocol
        </Link>
      </div>

      <footer className="mt-16 text-center text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-6 w-full">
        <p>
          SyntaxLens Research Application. Evaluation metrics indicate descriptive change in speech samples.
          Absence of an error in a short sample does not establish permanent acquisition.
        </p>
      </footer>
    </div>
  );
}
