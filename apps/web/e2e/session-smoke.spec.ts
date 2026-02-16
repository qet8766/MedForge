import fs from "node:fs";

import { expect, test, type Page } from "@playwright/test";

const DEFAULT_PASSWORD = "Password123!";

function resolveBaseURL(): string {
  return process.env.E2E_BASE_URL?.trim() || "http://medforge.localtest.me:18080";
}

function resolveDomain(baseURL: string): string {
  const fromEnv = process.env.E2E_DOMAIN?.trim();
  if (fromEnv) {
    return fromEnv;
  }

  const hostname = new URL(baseURL).hostname;
  if (hostname.startsWith("medforge.")) {
    return hostname.slice("medforge.".length);
  }

  throw new Error("Unable to infer E2E domain. Set E2E_DOMAIN explicitly.");
}

function resolveCredentials(): { email: string; password: string } {
  const defaultEmail = `e2e-${Date.now()}@medforge.test`;
  return {
    email: process.env.E2E_USER_EMAIL?.trim() || defaultEmail,
    password: process.env.E2E_USER_PASSWORD?.trim() || DEFAULT_PASSWORD,
  };
}

async function submitLogin(page: Page, email: string, password: string): Promise<"success" | "error"> {
  await page.goto("/auth/login");
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();

  try {
    await page.getByTestId("login-success").waitFor({ state: "visible", timeout: 8_000 });
    return "success";
  } catch {
    await page.getByTestId("login-error").waitFor({ state: "visible", timeout: 8_000 });
    return "error";
  }
}

async function ensureSignedIn(page: Page, email: string, password: string): Promise<void> {
  const loginResult = await submitLogin(page, email, password);
  if (loginResult === "success") {
    return;
  }

  await page.goto("/auth/signup");
  await page.getByTestId("signup-email").fill(email);
  await page.getByTestId("signup-password").fill(password);
  await page.getByTestId("signup-submit").click();
  await page.getByTestId("signup-success").waitFor({ state: "visible", timeout: 8_000 });

  await page.goto("/sessions");
  await page.getByTestId("session-logout").click();
  await expect(page.getByTestId("session-status")).toContainText("Signed out.");

  const postSignupLogin = await submitLogin(page, email, password);
  expect(postSignupLogin).toBe("success");
}

test("login -> create session -> open wildcard host -> websocket -> stop", async ({ page }) => {
  const baseURL = resolveBaseURL();
  const domain = resolveDomain(baseURL);
  const { email, password } = resolveCredentials();

  await ensureSignedIn(page, email, password);

  await page.goto("/sessions");
  await page.getByTestId("session-create").click();
  await page.getByTestId("session-current").waitFor({ state: "visible", timeout: 20_000 });

  const me = await page.evaluate(async () => {
    const response = await fetch("/api/me", {
      credentials: "include",
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return response.json() as Promise<{ user_id: string }>;
  });
  expect(me?.user_id).toBeTruthy();

  const slugRaw = await page.getByTestId("session-slug").textContent();
  const slug = slugRaw?.trim() || "";
  expect(slug).toMatch(/^[a-z0-9]{8}$/);

  const base = new URL(baseURL);
  const sessionOrigin = `${base.protocol}//s-${slug}.medforge.${domain}${base.port ? `:${base.port}` : ""}`;

  const sessionPage = await page.context().newPage();
  await sessionPage.setExtraHTTPHeaders({
    "X-User-Id": me?.user_id ?? "",
  });
  const websocketUrls: string[] = [];
  sessionPage.on("websocket", (ws) => websocketUrls.push(ws.url()));

  await sessionPage.goto(sessionOrigin, { waitUntil: "domcontentloaded" });
  await expect.poll(() => websocketUrls.length, { timeout: 30_000 }).toBeGreaterThan(0);
  await sessionPage.close();

  await page.getByTestId("session-stop").click();
  await expect(page.getByTestId("session-status")).toContainText("Session stopped.");

  const resultFile = process.env.E2E_RESULT_FILE?.trim();
  if (resultFile) {
    const result = {
      base_url: baseURL,
      session_url: sessionOrigin,
      slug,
      websocket_count: websocketUrls.length,
      timestamp: new Date().toISOString(),
    };
    fs.writeFileSync(resultFile, JSON.stringify(result, null, 2), "utf8");
  }
});
