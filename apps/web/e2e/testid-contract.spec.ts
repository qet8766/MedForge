import { expect, test } from "@playwright/test";

import { resolveCredentials, submitLogin } from "./helpers";

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
  });

  test("user menu signout testid", async ({ page }) => {
    await page.goto("/sessions");
    await page.getByRole("button", { name: /user menu/i }).click();
    await expect(page.getByTestId("user-menu-signout")).toBeVisible();
  });

  test("auth flow redirects to /sessions after login", async ({ browser }) => {
    const { email, password } = resolveCredentials();
    test.skip(!process.env.E2E_USER_EMAIL?.trim(), "E2E_USER_EMAIL required");

    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await ctx.newPage();

    const result = await submitLogin(page, email, password);
    expect(result).toBe("success");

    await page.waitForURL("**/sessions", { timeout: 10_000 });
    await expect(page.getByTestId("session-create")).toBeVisible();

    await ctx.close();
  });
});
