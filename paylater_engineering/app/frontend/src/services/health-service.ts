import { apiRequest } from "./api-client";
import type { HealthResponse } from "../types/api";

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", undefined, signal);
}
