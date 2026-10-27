/**
 * SyntaxLens Web API Client.
 *
 * Automatically handles:
 * - Cookie credential inclusion (credentials: 'include')
 * - CSRF token extraction from 'syntaxlens_csrf' cookie into 'X-CSRF-Token' header
 * - Unified JSON error parsing
 */

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "participant" | "researcher_admin" | "reviewer";
  is_active: boolean;
  must_change_password: boolean;
  participant_id?: string | null;
  participant_code?: string | null;
  study_group?: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  detail?: string | null;
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

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  distinct_actions?: string[];
  distinct_roles?: string[];
}

function getCsrfTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^| )syntaxlens_csrf=([^;]+)"));
  if (match && typeof match[2] === "string") {
    return decodeURIComponent(match[2]);
  }
  return null;
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = process.env["NEXT_PUBLIC_API_URL"] || "http://localhost:8000/api/v1";
  const normalizedEndpoint = endpoint.startsWith("/api/v1") ? endpoint.slice(7) : endpoint;
  const url = `${baseUrl}${normalizedEndpoint}`;

  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  // Attach CSRF header on mutating requests
  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfTokenFromCookie();
    if (csrfToken && !headers.has("X-CSRF-Token")) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        code: `HTTP_${response.status}`,
        message: response.statusText || "Request failed",
        request_id: "unknown",
      };
    }
    throw errorData;
  }

  return response.json();
}
