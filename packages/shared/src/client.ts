import { HealthResponse, ReadinessResponse, ErrorResponse } from "./api-types";

export interface ApiClientConfig {
  baseUrl: string;
  defaultHeaders?: Record<string, string>;
}

export class ApiError extends Error {
  public code: string;
  public requestId: string;
  public status: number;
  public detail?: string | null;

  constructor(status: number, errorData: ErrorResponse) {
    super(errorData.message);
    this.name = "ApiError";
    this.status = status;
    this.code = errorData.code;
    this.requestId = errorData.request_id;
    this.detail = errorData.detail;
  }
}

export class SyntaxLensClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, "");
    this.defaultHeaders = {
      "Content-Type": "application/json",
      ...config.defaultHeaders,
    };
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const headers = {
      ...this.defaultHeaders,
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errData: ErrorResponse;
      try {
        errData = (await response.json()) as ErrorResponse;
      } catch {
        errData = {
          code: "UNKNOWN_ERROR",
          message: `HTTP Error ${response.status}: ${response.statusText}`,
          request_id: response.headers.get("x-request-id") || "none",
        };
      }
      throw new ApiError(response.status, errData);
    }

    return (await response.json()) as T;
  }

  public async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  public async getReadiness(): Promise<ReadinessResponse> {
    return this.request<ReadinessResponse>("/ready");
  }
}
