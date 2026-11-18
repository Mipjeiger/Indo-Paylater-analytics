import { apiRequest } from "./api-client";
import type {
  AuditEvent,
  BorrowerRecord,
  DecisionRecord,
  ModelVersionRecord,
  PaginatedResponse,
  PortfolioSummary,
} from "../types/api";

export function getBorrowers(limit = 50, offset = 0, search?: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (search) params.set("search", search);
  return apiRequest<PaginatedResponse<BorrowerRecord>>(`/api/v1/borrowers?${params}`, undefined, signal);
}

export function getDecisions(limit = 50, offset = 0, signal?: AbortSignal) {
  return apiRequest<PaginatedResponse<DecisionRecord>>(
    `/api/v1/decisions?limit=${limit}&offset=${offset}`,
    undefined,
    signal,
  );
}

export function getPortfolioSummary(signal?: AbortSignal) {
  return apiRequest<PortfolioSummary>("/api/v1/portfolio/summary", undefined, signal);
}

export function getModels(signal?: AbortSignal) {
  return apiRequest<{ items: ModelVersionRecord[] }>("/api/v1/models", undefined, signal);
}

export function getAuditEvents(limit = 100, signal?: AbortSignal) {
  return apiRequest<{ items: AuditEvent[] }>(`/api/v1/audit/events?limit=${limit}`, undefined, signal);
}
