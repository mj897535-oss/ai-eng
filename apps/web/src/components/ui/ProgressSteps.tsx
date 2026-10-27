import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Step {
  id: string;
  title: string;
  description?: string;
}

export interface ProgressStepsProps {
  steps: Step[];
  currentStepIndex: number;
  className?: string;
}

export function ProgressSteps({ steps, currentStepIndex, className }: ProgressStepsProps) {
  return (
    <nav aria-label="Progress" className={cn("w-full py-4", className)}>
      <ol className="flex items-center justify-between w-full">
        {steps.map((step, index) => {
          const isCompleted = index < currentStepIndex;
          const isCurrent = index === currentStepIndex;

          return (
            <li key={step.id} className="relative flex-1 flex flex-col items-center">
              {/* Connector line */}
              {index !== 0 && (
                <div
                  aria-hidden="true"
                  className={cn(
                    "absolute top-4 right-[50%] w-full h-0.5 -translate-y-1/2 transition-colors",
                    isCompleted ? "bg-indigo-600 dark:bg-indigo-500" : "bg-slate-200 dark:bg-slate-800"
                  )}
                />
              )}

              {/* Step circle */}
              <div
                className={cn(
                  "relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 text-xs font-bold transition-all",
                  isCompleted && "bg-indigo-600 border-indigo-600 text-white dark:bg-indigo-500 dark:border-indigo-500",
                  isCurrent && "border-indigo-600 bg-white text-indigo-600 dark:border-indigo-400 dark:bg-slate-900 dark:text-indigo-400 ring-4 ring-indigo-50 dark:ring-indigo-950/40",
                  !isCompleted && !isCurrent && "border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-500"
                )}
                aria-current={isCurrent ? "step" : undefined}
              >
                {isCompleted ? <Check className="w-4 h-4 stroke-[3]" /> : index + 1}
              </div>

              {/* Title */}
              <span
                className={cn(
                  "mt-2 text-xs font-medium text-center",
                  isCurrent && "font-bold text-indigo-700 dark:text-indigo-400",
                  isCompleted && "text-slate-800 dark:text-slate-200",
                  !isCompleted && !isCurrent && "text-slate-400 dark:text-slate-500"
                )}
              >
                {step.title}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
