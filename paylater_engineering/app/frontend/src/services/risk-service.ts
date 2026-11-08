import { apiRequest } from "./api-client";
import type { DtiResponse, RootCauseResponse, Twp90Request, Twp90Response } from "../types/api";

export function assessTwp90(request: Twp90Request, signal?: AbortSignal): Promise<Twp90Response> {
  return apiRequest<Twp90Response>("/score/twp90", {
    method: "POST",
    body: JSON.stringify(request),
  }, signal);
}

export function assessDti(
  borrowerId: string,
  features: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<DtiResponse> {
  const query = encodeURIComponent(JSON.stringify(features));
  return apiRequest<DtiResponse>(`/score/dti-distress/${encodeURIComponent(borrowerId)}?features=${query}`, undefined, signal);
}

export function classifyRootCause(
  borrowerId: string,
  request: Twp90Request,
  signal?: AbortSignal,
): Promise<RootCauseResponse> {
  return apiRequest<RootCauseResponse>(`/classify/root-cause/${encodeURIComponent(borrowerId)}`, {
    method: "POST",
    body: JSON.stringify(request),
  }, signal);
}
