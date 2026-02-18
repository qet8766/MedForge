const API_URL = process.env.API_URL?.trim() ?? "";
const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL?.trim() ?? "";
const DOMAIN = process.env.DOMAIN?.trim() ?? "";
const NEXT_PUBLIC_DOMAIN = process.env.NEXT_PUBLIC_DOMAIN?.trim() ?? "";
const DEFAULT_API_DOMAIN = "medforge.example.com";
const API_BASE_FALLBACK = NEXT_PUBLIC_DOMAIN
  ? `https://api.${NEXT_PUBLIC_DOMAIN}`
  : DOMAIN ? `https://api.${DOMAIN}` : `https://api.${DEFAULT_API_DOMAIN}`;

function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return API_URL || NEXT_PUBLIC_API_URL || API_BASE_FALLBACK;
  }
  // Derive from browser hostname — always correct regardless of build-time env vars
  const match = window.location.hostname.match(/medforge\.[a-z0-9.-]+$/i);
  if (match) return `https://api.${match[0]}`;
  // Fallback for non-medforge hostnames (e.g., localhost dev)
  return NEXT_PUBLIC_API_URL || API_BASE_FALLBACK;
}

const ROOT_LEVEL_PATHS = ["/healthz"];

function normalizeApiPath(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with '/': ${path}`);
  }
  if (path === "/api/v2" || path.startsWith("/api/v2/")) {
    return path;
  }
  if (ROOT_LEVEL_PATHS.includes(path)) {
    return path;
  }
  throw new Error(`API path must start with '/api/v2': ${path}`);
}

export function toApiUrl(path: string): string {
  const normalizedPath = normalizeApiPath(path);
  const base = resolveApiBase();
  if (base) {
    return `${base}${normalizedPath}`;
  }
  return normalizedPath;
}
