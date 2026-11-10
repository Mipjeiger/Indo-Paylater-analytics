import { apiRequest } from "./api-client";
import type { HealthResponse } from "../types/api";

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health/", undefined, signal);
}

export async function getMetrics(signal?: AbortSignal): Promise<string> {
  const response = await fetch(
    `${(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")}/metrics/`,
    { signal, headers: { Accept: "text/plain" } },
  );
  if (!response.ok) {
    throw new Error(`Metrics request failed with status ${response.status}`);
  }
  return response.text();
}
