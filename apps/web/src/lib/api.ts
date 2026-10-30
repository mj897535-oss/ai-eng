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
  let baseUrl = process.env["NEXT_PUBLIC_API_URL"] || "/api/v1";

  // In the browser, always default to relative /api/v1 for unified fullstack container
  if (typeof window !== "undefined") {
    if (!process.env["NEXT_PUBLIC_API_URL"] || process.env["NEXT_PUBLIC_API_URL"].includes("localhost")) {
      baseUrl = "/api/v1";
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
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Attach CSRF header on mutating requests
  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfTokenFromCookie();
    if (csrfToken && !headers.has("X-CSRF-Token")) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (netErr: any) {
    throw {
      code: "NETWORK_ERROR",
      message: netErr?.message || "Network connection to SyntaxLens backend failed. Please check your connection or reload.",
      request_id: "client-net-error",
    } as ApiError;
  }

  if (!response.ok) {
    let errorData: ApiError;
    try {
      const rawText = await response.text();
      try {
        const json = JSON.parse(rawText);
        errorData = {
          code: json.code || `HTTP_${response.status}`,
          message: json.message || json.detail || response.statusText || `Request failed with status ${response.status}`,
          request_id: json.request_id || "unknown",
          detail: json.detail,
        };
      } catch {
        errorData = {
          code: `HTTP_${response.status}`,
          message: rawText.length > 0 && rawText.length < 200 ? rawText : (response.statusText || `Request failed with status ${response.status}. The backend may be starting up.`),
          request_id: "unknown",
        };
      }
    } catch {
      errorData = {
        code: `HTTP_${response.status}`,
        message: response.statusText || `Request failed (${response.status})`,
        request_id: "unknown",
      };
    }
    throw errorData;
  }

  return response.json();
}
