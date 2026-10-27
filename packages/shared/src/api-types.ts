/**
 * SyntaxLens Auto-Generated & Shared API Types.
 * Synchronized with OpenAPI schema from FastAPI backend.
 */

export interface HealthResponse {
  status: "healthy" | "degraded";
  service: string;
  environment: string;
  rubric_version: string;
  prompt_version: string;
  stt_provider: string;
  llm_provider: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded";
  database: "connected" | "disconnected";
  storage: "configured" | "error";
}

export interface ErrorResponse {
  code: string;
  message: string;
  request_id: string;
  detail?: string | null;
}

export type ErrorCategory =
  | "TNS"   // Tense and aspect
  | "SVA"   // Subject-verb agreement
  | "WO"    // Word order
  | "AUX"   // Auxiliary usage
  | "ART"   // Articles
  | "PREP"  // Prepositions
  | "PRO"   // Pronouns
  | "OTH";  // Other / uncertain / variation

export interface CategoryMetric {
  category_code: ErrorCategory;
  count: number;
  rate_per_100_words: number;
  observed: boolean;
  status_label: "observed" | "not observed in this sample";
}

export interface ComparativeMetricsResult {
  pre_word_count: number;
  post_word_count: number;
  pre_error_count: number;
  post_error_count: number;
  pre_rate_per_100: number;
  post_rate_per_100: number;
  absolute_reduction: number;
  relative_reduction_pct: number | null;
  relative_reduction_status: "defined" | "undefined_zero_baseline";
  scientific_disclaimer: string;
}

export type UserRole = "student" | "researcher" | "reviewer" | "admin";
export type StudyGroup = "intervention" | "control";
export type ConsentStatus = "consented" | "withdrawn";
export type AssessmentType = "pre" | "post";
export type ReviewDecisionType = "accepted" | "rejected" | "edited" | "uncertain";
export type AttemptType = "independent" | "hint_assisted" | "revealed";
