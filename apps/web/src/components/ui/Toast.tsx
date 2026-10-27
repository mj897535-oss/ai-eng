"use client";

import * as React from "react";
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ToastProps {
  id: string;
  type?: "info" | "success" | "warning" | "error";
  title: string;
  description?: string;
  onDismiss?: (id: string) => void;
}

export function Toast({ id, type = "info", title, description, onDismiss }: ToastProps) {
  const icons = {
    info: <Info className="w-5 h-5 text-indigo-500" />,
    success: <CheckCircle2 className="w-5 h-5 text-emerald-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
    error: <AlertCircle className="w-5 h-5 text-rose-500" />,
  };

  const borders = {
    info: "border-indigo-200 dark:border-indigo-900/50",
    success: "border-emerald-200 dark:border-emerald-900/50",
    warning: "border-amber-200 dark:border-amber-900/50",
    error: "border-rose-200 dark:border-rose-900/50",
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-start gap-3 w-full max-w-sm rounded-xl p-4 shadow-lg border bg-white dark:bg-slate-900 transition-all",
        borders[type]
      )}
    >
      <div className="shrink-0 mt-0.5">{icons[type]}</div>
      <div className="flex-1 space-y-1">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h4>
        {description && <p className="text-xs text-slate-600 dark:text-slate-400">{description}</p>}
      </div>
      {onDismiss && (
        <button
          onClick={() => onDismiss(id)}
          className="shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md"
        >
          <X className="w-4 h-4" />
          <span className="sr-only">Dismiss</span>
        </button>
      )}
    </div>
  );
}
