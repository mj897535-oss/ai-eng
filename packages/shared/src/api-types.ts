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

// --- Phase P4 Participant, Consent & Onboarding Types ---

export type StudyGroup = "intervention" | "control";

export interface Participant {
  participant_id: string;
  research_code: string;
  study_group: StudyGroup;
  is_group_blinded: boolean;
  is_active: boolean;
  is_withdrawn: boolean;
  age?: number | null;
  age_band?: string | null;
  mother_tongue?: string | null;
  school_medium?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  current_consent_version?: string | null;
  consented_at?: string | null;
  withdrawn_at?: string | null;
  withdrawal_reason?: string | null;
  onboarding_completed: boolean;
  onboarding_step: "consent" | "profile" | "mic_check" | "what_next" | "completed" | "withdrawn";
  created_at: string;
}

export interface CSVRowValidation {
  row_number: number;
  research_code: string;
  study_group: string;
  email?: string | null;
  age?: number | null;
  age_band?: string | null;
  mother_tongue?: string | null;
  school_medium?: string | null;
  country?: string | null;
  state?: string | null;
  city?: string | null;
  is_valid: boolean;
  error_reason?: string | null;
}

export interface CSVImportResult {
  dry_run: boolean;
  total_rows: number;
  valid_count: number;
  rejected_count: number;
  duplicate_count: number;
  valid_rows: CSVRowValidation[];
  rejected_rows: CSVRowValidation[];
  duplicates_found: Array<{ row_number: number; research_code: string; reason: string }>;
  can_commit: boolean;
}

export interface ConsentDocument {
  version: string;
  effective_date: string;
  title: string;
  text: string;
  withdrawal_policy: string;
  already_consented: boolean;
  consented_version?: string | null;
  is_withdrawn: boolean;
}

export interface OnboardingState {
  participant_id: string;
  research_code: string;
  onboarding_completed: boolean;
  current_step: "consent" | "profile" | "mic_check" | "what_next" | "completed" | "withdrawn";
  is_withdrawn: boolean;
  consent_status: {
    agreed: boolean;
    version?: string | null;
    consented_at?: string | null;
  };
  profile: {
    age?: number | null;
    age_band?: string | null;
    mother_tongue?: string | null;
    school_medium?: string | null;
    country?: string | null;
    state?: string | null;
    city?: string | null;
  };
  config: {
    collect_name: boolean;
    age_collection_mode: "exact" | "band";
    collect_geography: boolean;
    current_consent_version: string;
  };
}

