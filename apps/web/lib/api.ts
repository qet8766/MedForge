export type CompetitionSummary = {
  slug: string;
  title: string;
  competition_tier: "public" | "private";
  metric: string;
  metric_version: string;
  scoring_mode: string;
  leaderboard_rule: string;
  evaluation_policy: string;
  competition_spec_version: string;
  is_permanent: boolean;
  submission_cap_per_day: number;
};
export type CompetitionDetail = CompetitionSummary & {
  description: string;
  status: string;
  dataset_slug: string;
  dataset_title: string;
};
export type LeaderboardEntry = {
  rank: number;
  user_id: string;
  best_submission_id: string;
  best_score_id: string;
  primary_score: number;
  metric_version: string;
  evaluation_split_version: string;
  scored_at: string | null;
};
export type DatasetSummary = {
  slug: string;
  title: string;
  source: string;
};
export type DatasetDetail = DatasetSummary & {
  license: string;
  storage_path: string;
  bytes: number;
  checksum: string;
};
export type AuthUser = {
  user_id: string;
  email: string;
  role: "user" | "admin";
};
export type MeResponse = {
  user_id: string;
  role: "user" | "admin";
  email: string | null;
};
export type SessionStatus = "starting" | "running" | "stopping" | "stopped" | "error";
export type SessionRead = {
  id: string;
  user_id: string;
  tier: "public" | "private";
  pack_id: string;
  status: SessionStatus;
  container_id: string | null;
  gpu_id: number;
  slug: string;
  workspace_zfs: string;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  error_message: string | null;
};
export type SessionCreateResponse = {
  message: string;
  session: SessionRead;
};
export type SessionActionResponse = {
  message: string;
};
export type SessionCurrentResponse = {
  session: SessionRead | null;
};
export type ApiMeta = {
  request_id: string;
  api_version: string;
  timestamp: string;
  limit?: number | null;
  next_cursor?: string | null;
  has_more?: boolean | null;
};
export type ApiEnvelope<T> = {
  data: T;
  meta: ApiMeta;
};
const API_URL = process.env.API_URL?.trim() ?? "";
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() ?? "";
const DOMAIN = process.env.DOMAIN?.trim() ?? "";
const NEXT_PUBLIC_DOMAIN = process.env.NEXT_PUBLIC_DOMAIN?.trim() ?? "";
const API_BASE_FALLBACK = NEXT_PUBLIC_DOMAIN
  ? `https://api.medforge.${NEXT_PUBLIC_DOMAIN}`
  : DOMAIN ? `https://api.medforge.${DOMAIN}` : "";
const DEFAULT_SERVER_API_URL = "http://127.0.0.1:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  if (!isRecord(value)) {
    return false;
  }
  return "data" in value && "meta" in value;
}

function extractApiErrorMessage(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return fallback;
  }

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  const title = payload.title;
  if (typeof title === "string" && title.trim()) {
    return title;
  }

  return fallback;
}

async function parseJsonBody(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return API_URL || NEXT_PUBLIC_API_URL || API_BASE_FALLBACK || DEFAULT_SERVER_API_URL;
  }
  return NEXT_PUBLIC_API_URL || API_BASE_FALLBACK;
}

function toApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  const base = resolveApiBase();
  if (base) {
    return `${base}${path}`;
  }
  return path;
}
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(toApiUrl(path), {
    cache: "no-store",
    credentials: "include"
  });
  const payload = await parseJsonBody(res);
  if (!res.ok) {
    throw new Error(extractApiErrorMessage(payload, `GET ${path} failed: ${res.status}`));
  }
  if (!isEnvelope<T>(payload)) {
    throw new Error(`GET ${path} returned an invalid response envelope.`);
  }
  return payload.data;
}
export async function apiSubmitFile<TResponse>(path: string, file: File): Promise<TResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(toApiUrl(path), {
    method: "POST",
    credentials: "include",
    body: form
  });
  const payload = await parseJsonBody(res);
  if (!res.ok) {
    throw new Error(extractApiErrorMessage(payload, `POST ${path} failed: ${res.status}`));
  }
  if (!isEnvelope<TResponse>(payload)) {
    throw new Error(`POST ${path} returned an invalid response envelope.`);
  }
  return payload.data;
}
export async function apiPostJson<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  const res = await fetch(toApiUrl(path), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  const body = await parseJsonBody(res);
  if (!res.ok) {
    throw new Error(extractApiErrorMessage(body, `POST ${path} failed: ${res.status}`));
  }
  if (!isEnvelope<TResponse>(body)) {
    throw new Error(`POST ${path} returned an invalid response envelope.`);
  }
  return body.data;
}
