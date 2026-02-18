import { ApiRequestError } from "@/lib/api-error";
import { requestEnvelope } from "@/lib/api-core";

export { ApiRequestError };

export type {
  ApiEnvelope,
  ApiMeta,
  ApiProblem,
  AuthUser,
  CompetitionDetail,
  CompetitionSummary,
  DatasetDetail,
  DatasetFileEntry,
  DatasetSummary,
  GpuStatusData,
  HealthResponse,
  LeaderboardEntry,
  LeaderboardResponse,
  MeResponse,
  MeUpdateRequest,
  PlatformStatsData,
  ScoreStatus,
  ServerStatusResponse,
  SessionActionResponse,
  SessionCreateResponse,
  SessionCurrentResponse,
  SessionListItem,
  SessionRead,
  SessionStatus,
  SessionSummaryData,
  StorageInfoData,
  SubmissionCreateResponse,
  SubmissionRead,
  SubmissionScoreRead,
  SystemInfoData,
  UserAdminRead,
  UserUpdateRequest,
} from "@/lib/contracts";

export async function apiGet<T>(path: string): Promise<T> {
  return requestEnvelope<T>(path, { cache: "no-store" });
}

export async function apiSubmitFile<TResponse>(path: string, file: File): Promise<TResponse> {
  const form = new FormData();
  form.append("file", file);
  return requestEnvelope<TResponse>(path, { method: "POST", body: form });
}

export async function apiPostJson<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  return requestEnvelope<TResponse>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function apiPatchJson<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  return requestEnvelope<TResponse>(path, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}
