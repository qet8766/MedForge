import { expect, test } from "@playwright/test";

test.describe("public pages", () => {
  test("landing page renders hero and feature cards", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);

    await expect(page.locator("h1")).toContainText("MedForge");
    await expect(page.getByText("GPU Sessions")).toBeVisible();
    await expect(page.getByText("Competitions").first()).toBeVisible();
    await expect(page.getByText("Leaderboards").first()).toBeVisible();

    await expect(page.locator('a[href="/auth/signup"]').first()).toBeVisible();
    await expect(page.locator('a[href="/competitions"]').first()).toBeVisible();
  });

  test("login page renders form", async ({ page }) => {
    const response = await page.goto("/auth/login");
    expect(response?.status()).toBe(200);

    await expect(page.getByText("Welcome back")).toBeVisible();
    await expect(page.getByText("Sign in to your MedForge account")).toBeVisible();
    await expect(page.locator('a[href="/auth/signup"]').first()).toBeVisible();
  });

  test("signup page renders form", async ({ page }) => {
    const response = await page.goto("/auth/signup");
    expect(response?.status()).toBe(200);

    await expect(page.getByText("Create account").first()).toBeVisible();
    await expect(page.getByText("Get started with MedForge")).toBeVisible();
    await expect(page.locator('a[href="/auth/login"]').first()).toBeVisible();
  });
});
