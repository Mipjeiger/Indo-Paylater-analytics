import { apiRequest } from "./api-client";
import type { DashboardKpis } from "../types/api";

export function getDashboardKpis(signal?: AbortSignal): Promise<DashboardKpis> {
  return apiRequest<DashboardKpis>("/api/v1/dashboard/kpis", undefined, signal);
}
