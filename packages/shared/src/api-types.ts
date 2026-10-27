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

export type UserRole = "participant" | "researcher_admin" | "reviewer";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  must_change_password: boolean;
  participant_id?: string | null;
  participant_code?: string | null;
}

export interface LoginResponse {
  user: UserResponse;
  csrf_token: string;
  message: string;
}

export interface AuditLogItem {
  log_id: string;
  actor_id: string | null;
  role: string | null;
  action: string;
  record_type: string;
  record_id: string;
  outcome: string;
  ip_hash: string | null;
  user_agent: string | null;
  details: string | null;
  timestamp: string;
}

export interface PaginatedAuditLogResponse {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
  distinct_actions: string[];
  distinct_roles: string[];
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
  relative_reduction: number | null;
  relative_reduction_formatted: string;
  category_breakdown: Record<string, { pre_count: number; post_count: number; pre_rate: number; post_rate: number }>;
}
