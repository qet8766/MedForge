import { headers } from "next/headers";

import { Surface, surfaceFromHostname } from "@/lib/surface";

export async function inferServerSurface(): Promise<Surface> {
  const headerStore = await headers();
  const hostHeader = headerStore.get("x-forwarded-host") ?? headerStore.get("host") ?? "";
  const hostname = hostHeader.split(":", 1)[0];
  return surfaceFromHostname(hostname);
}
