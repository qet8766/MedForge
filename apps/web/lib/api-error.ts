import type { ApiProblem } from "@/lib/contracts";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseProblem(payload: unknown): ApiProblem | null {
  if (!isRecord(payload)) {
    return null;
  }

  const type = payload.type;
  const title = payload.title;
  const status = payload.status;
  const detail = payload.detail;
  const instance = payload.instance;
  const code = payload.code;
  const requestId = payload.request_id;

  if (
    typeof type !== "string" ||
    typeof title !== "string" ||
    typeof status !== "number" ||
    typeof detail !== "string" ||
    typeof instance !== "string" ||
    typeof code !== "string" ||
    typeof requestId !== "string"
  ) {
    return null;
  }

  const errors = Array.isArray(payload.errors) && payload.errors.every(isRecord) ? payload.errors : undefined;

  return {
    type,
    title,
    status,
    detail,
    instance,
    code,
    request_id: requestId,
    errors
  };
}

export async function parseJsonBody(res: Response): Promise<unknown> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export class ApiRequestError extends Error {
  readonly method: string;
  readonly path: string;
  readonly status: number;
  readonly code: string | null;
  readonly requestId: string | null;
  readonly errors: Record<string, unknown>[] | null;

  constructor({ message, method, path, status, code, requestId, errors }: ApiRequestErrorInit) {
    super(message);
    this.name = "ApiRequestError";
    this.method = method;
    this.path = path;
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.errors = errors;
  }
}

type ApiRequestErrorInit = {
  message: string;
  method: string;
  path: string;
  status: number;
  code: string | null;
  requestId: string | null;
  errors: Record<string, unknown>[] | null;
};

export function buildApiError(path: string, method: string, status: number, payload: unknown): ApiRequestError {
  const problem = parseProblem(payload);
  const message = problem?.detail?.trim() || problem?.title?.trim() || `${method} ${path} failed: ${status}`;
  return new ApiRequestError({
    message,
    method,
    path,
    status,
    code: problem?.code ?? null,
    requestId: problem?.request_id ?? null,
    errors: problem?.errors ?? null
  });
}
