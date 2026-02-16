export type CompetitionSummary = {
  slug: string;
  title: string;
  competition_tier: "PUBLIC" | "PRIVATE";
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
  tier: "PUBLIC" | "PRIVATE";
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
  detail: string;
  session: SessionRead;
};
export type SessionStopResponse = {
  detail: string;
  session: SessionRead;
};
export type SessionCurrentResponse = {
  session: SessionRead | null;
};
const API_URL = process.env.API_URL?.trim() ?? "";
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() ?? "";
const DOMAIN = process.env.DOMAIN?.trim() ?? "";
const NEXT_PUBLIC_DOMAIN = process.env.NEXT_PUBLIC_DOMAIN?.trim() ?? "";
const API_BASE_FALLBACK = NEXT_PUBLIC_DOMAIN
  ? `https://api.medforge.${NEXT_PUBLIC_DOMAIN}`
  : DOMAIN ? `https://api.medforge.${DOMAIN}` : "";
const DEFAULT_SERVER_API_URL = "http://127.0.0.1:8000";
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
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}
export async function apiSubmitFile(path: string, file: File): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(toApiUrl(path), {
    method: "POST",
    credentials: "include",
    body: form
  });
  const payload = await res.json();
  if (!res.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "Submission failed";
    throw new Error(detail);
  }
  return payload;
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
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const detail = typeof (body as { detail?: unknown } | null)?.detail === "string"
      ? (body as { detail: string }).detail
      : `POST ${path} failed: ${res.status}`;
    throw new Error(detail);
  }
  return body as TResponse;
}
