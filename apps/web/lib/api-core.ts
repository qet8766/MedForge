import type { ApiEnvelope } from "@/lib/contracts";

import { buildApiError, parseJsonBody } from "@/lib/api-error";
import { toApiUrl } from "@/lib/api-url";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  if (!isRecord(value)) {
    return false;
  }
  return "data" in value && "meta" in value;
}

export async function requestEnvelope<T>(path: string, init: RequestInit): Promise<T> {
  const method = init.method ?? "GET";
  const res = await fetch(toApiUrl(path), {
    credentials: "include",
    ...init
  });
  const payload = await parseJsonBody(res);
  if (!res.ok) {
    throw buildApiError(path, method, res.status, payload);
  }
  if (!isEnvelope<T>(payload)) {
    throw new Error(`${method} ${path} returned an invalid response envelope.`);
  }
  return payload.data;
}
