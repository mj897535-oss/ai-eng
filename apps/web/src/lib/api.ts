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
  let baseUrl = process.env["NEXT_PUBLIC_API_URL"] || "http://localhost:8000/api/v1";

  // Auto-detect production Render domain if NEXT_PUBLIC_API_URL was defaulted to localhost
  if (typeof window !== "undefined") {
    if (!process.env["NEXT_PUBLIC_API_URL"] || process.env["NEXT_PUBLIC_API_URL"].includes("localhost")) {
      if (window.location.hostname.endsWith(".onrender.com")) {
        const parts = window.location.hostname.split(".");
        // e.g. syntaxlens-web -> syntaxlens-api
        const prefix = parts[0] ?? "syntaxlens-web";
        const apiHost = prefix.replace(/-web$/, "-api");
        baseUrl = `https://${apiHost}.onrender.com/api/v1`;
      }
    }
  }

  // Normalize baseUrl so it always ends with /api/v1 and has no trailing slashes
  baseUrl = baseUrl.replace(/\/+$/, "");
  if (!baseUrl.endsWith("/api/v1")) {
    baseUrl = `${baseUrl}/api/v1`;
  }

  const normalizedEndpoint = endpoint.startsWith("/api/v1") ? endpoint.slice(7) : endpoint;
  const cleanEndpoint = normalizedEndpoint.startsWith("/") ? normalizedEndpoint : `/${normalizedEndpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

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
