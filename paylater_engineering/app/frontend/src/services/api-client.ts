import type { ApiError } from "../types/api";

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw { status: 0, message: "The API is unavailable. Check the backend connection." } satisfies ApiError;
  }

  if (!response.ok) {
    const body = await response.text();
    throw {
      status: response.status,
      message: body || `Request failed with status ${response.status}`,
    } satisfies ApiError;
  }
  return (await response.json()) as T;
}

export function getApiBaseUrl(): string {
  return baseUrl;
}
