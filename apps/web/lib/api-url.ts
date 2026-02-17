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

export function normalizeApiPath(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  if (path === "/api/v1" || path.startsWith("/api/v1/")) {
    return path;
  }
  throw new Error(`API path must start with '/api/v1': ${path}`);
}

export function toApiUrl(path: string): string {
  const normalizedPath = normalizeApiPath(path);
  const base = resolveApiBase();
  if (base) {
    return `${base}${normalizedPath}`;
  }
  return normalizedPath;
}
