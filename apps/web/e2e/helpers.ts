import { expect, type Page } from "@playwright/test";

export const AUTH_STATE_PATH = "e2e/.auth/user.json";

const DEFAULT_PASSWORD = "Password123!";

export function resolveBaseURL(): string {
  const explicit = process.env.E2E_BASE_URL?.trim();
  if (explicit) {
    return explicit;
  }

  const domain = process.env.E2E_DOMAIN?.trim() || process.env.DOMAIN?.trim() || "";
  if (domain) {
    return `https://medforge.${domain}`;
  }

  throw new Error("E2E_BASE_URL (or E2E_DOMAIN/DOMAIN) is required for remote-external e2e.");
}

export function resolveDomain(baseURL: string): string {
  const fromEnv = process.env.E2E_DOMAIN?.trim();
  if (fromEnv) {
    return fromEnv;
  }

  const hostname = new URL(baseURL).hostname;
  if (hostname.startsWith("external.medforge.")) {
    return hostname.slice("external.medforge.".length);
  }
  if (hostname.startsWith("internal.medforge.")) {
    return hostname.slice("internal.medforge.".length);
  }
  if (hostname.startsWith("medforge.")) {
    return hostname.slice("medforge.".length);
  }

  throw new Error("Unable to infer E2E domain. Set E2E_DOMAIN explicitly.");
}

export function resolveCredentials(): { email: string; password: string } {
  const defaultEmail = `e2e-${Date.now()}@medforge.test`;
  return {
    email: process.env.E2E_USER_EMAIL?.trim() || defaultEmail,
    password: process.env.E2E_USER_PASSWORD?.trim() || DEFAULT_PASSWORD,
  };
}

export async function submitLogin(page: Page, email: string, password: string): Promise<"success" | "error"> {
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

export async function ensureSignedIn(page: Page, email: string, password: string): Promise<void> {
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
