export type Surface = "external" | "internal";

export function surfaceFromHostname(hostname: string): Surface {
  const normalized = hostname.toLowerCase();
  if (
    normalized === "internal" ||
    normalized.startsWith("internal.medforge.") ||
    normalized.includes(".internal.medforge.")
  ) {
    return "internal";
  }
  return "external";
}

export function inferClientSurface(): Surface {
  if (typeof window === "undefined") {
    return "external";
  }
  return surfaceFromHostname(window.location.hostname);
}

export function apiPathForSurface(surface: Surface, path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `/api/v2/${surface}${normalized}`;
}

export function surfaceHost(surface: Surface, domain: string): string {
  return `${surface}.medforge.${domain}`;
}
