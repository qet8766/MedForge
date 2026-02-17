import { expect, test } from "@playwright/test";

import { resolveCredentials } from "./helpers";

test.describe("data-testid contracts", () => {
  test("login form testids", async ({ browser }) => {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await ctx.newPage();

    await page.goto("/auth/login");
    await expect(page.getByTestId("login-form")).toBeVisible();
    await expect(page.getByTestId("login-email")).toBeVisible();
    await expect(page.getByTestId("login-password")).toBeVisible();
    await expect(page.getByTestId("login-submit")).toBeVisible();

    expect(await page.getByTestId("login-success").count()).toBe(0);
    expect(await page.getByTestId("login-error").count()).toBe(0);

    await ctx.close();
  });

  test("signup form testids", async ({ browser }) => {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await ctx.newPage();

    await page.goto("/auth/signup");
    await expect(page.getByTestId("signup-form")).toBeVisible();
    await expect(page.getByTestId("signup-email")).toBeVisible();
    await expect(page.getByTestId("signup-password")).toBeVisible();
    await expect(page.getByTestId("signup-submit")).toBeVisible();

    expect(await page.getByTestId("signup-success").count()).toBe(0);

    await ctx.close();
  });

  test("session controls testids", async ({ page }) => {
    await page.goto("/sessions");
    await expect(page.getByTestId("session-create")).toBeVisible();
    await expect(page.getByTestId("session-stop")).toBeVisible();
    await expect(page.getByTestId("session-whoami")).toBeVisible();
    await expect(page.getByTestId("session-logout")).toBeVisible();
    await expect(page.getByTestId("session-status")).toBeVisible();

    expect(await page.getByTestId("session-error").count()).toBeLessThanOrEqual(1);
  });

  test("auth flow redirects to /sessions after login", async ({ browser }) => {
    const email = process.env.E2E_USER_EMAIL?.trim();
    const password = process.env.E2E_USER_PASSWORD?.trim();
    test.skip(!email || !password, "E2E_USER_EMAIL and E2E_USER_PASSWORD required");

    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await ctx.newPage();

    await page.goto("/auth/login");
    await page.getByTestId("login-email").fill(email!);
    await page.getByTestId("login-password").fill(password!);
    await page.getByTestId("login-submit").click();
    await page.getByTestId("login-success").waitFor({ state: "visible", timeout: 8_000 });

    await page.waitForURL("**/sessions", { timeout: 10_000 });
    await expect(page.getByTestId("session-create")).toBeVisible();

    await ctx.close();
  });
});
