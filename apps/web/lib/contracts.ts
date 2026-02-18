export type CompetitionSummary = {
  slug: string;
  title: string;
  competition_exposure: "external" | "internal";
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
  status: "active";
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

export type LeaderboardResponse = {
  competition_slug: string;
  entries: LeaderboardEntry[];
};

export type DatasetSummary = {
  slug: string;
  title: string;
  source: string;
  exposure: "external" | "internal";
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
  can_use_internal: boolean;
};

export type MeResponse = {
  user_id: string;
  role: "user" | "admin";
  email: string | null;
  can_use_internal: boolean;
  ssh_public_key: string | null;
};

export type SessionStatus = "starting" | "running" | "stopping" | "stopped" | "error";

export type SessionRead = {
  id: string;
  user_id: string;
  exposure: "external" | "internal";
  pack_id: string;
  status: SessionStatus;
  container_id: string | null;
  gpu_id: number;
  ssh_port: number;
  ssh_host: string;
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

export type ApiProblemValidationError = Record<string, unknown>;

export type ApiProblem = {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  request_id: string;
  errors?: ApiProblemValidationError[];
};

export type ScoreStatus = "queued" | "scoring" | "scored" | "failed";

export type SubmissionScoreRead = {
  id: string;
  primary_score: number;
  score_components: Record<string, number>;
  scorer_version: string;
  metric_version: string;
  evaluation_split_version: string;
  manifest_sha256: string;
  created_at: string;
};

export type SubmissionRead = {
  id: string;
  competition_slug: string;
  user_id: string;
  filename: string;
  score_status: ScoreStatus;
  score_error: string | null;
  created_at: string;
  scored_at: string | null;
  official_score: SubmissionScoreRead | null;
};

export type SubmissionCreateResponse = {
  submission: SubmissionRead;
  daily_cap: number;
  remaining_today: number;
};

export type HealthResponse = {
  status: "ok" | "degraded";
};

export type UserAdminRead = {
  user_id: string;
  email: string;
  role: "user" | "admin";
  can_use_internal: boolean;
  max_concurrent_sessions: number;
  created_at: string;
  active_session_count: number;
};

export type UserUpdateRequest = {
  role?: "user" | "admin";
  can_use_internal?: boolean;
  max_concurrent_sessions?: number;
};

export type MeUpdateRequest = {
  email?: string;
  current_password?: string;
  new_password?: string;
  ssh_public_key?: string | null;
};

export type SessionListItem = SessionRead & {
  user_email?: string;
};
