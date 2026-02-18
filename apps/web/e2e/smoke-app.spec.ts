import { expect, test } from "@playwright/test";

import { resolveApiBaseURL } from "./helpers";

test.describe("authenticated app pages", () => {
  test("dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Welcome back").first()).toBeVisible();
    await expect(page.locator("main").getByText("Competitions")).toBeVisible();
    await expect(page.getByText("Session Status").first()).toBeVisible();
    await expect(page.getByText("Quick Actions").first()).toBeVisible();
  });

  test("sessions", async ({ page }) => {
    await page.goto("/sessions");
    await expect(page.locator("h1").first()).toContainText("Sessions");
    await expect(page.locator("main").getByText("Session History")).toBeVisible();
  });

  test("competitions listing", async ({ page }) => {
    await page.goto("/competitions");
    await expect(page.locator("main").getByText("Competitions")).toBeVisible();

    const cards = page.locator('a[href^="/competitions/"]');
    const count = await cards.count();
    if (count > 0) {
      await expect(cards.first()).toBeVisible();
    } else {
      await expect(page.getByText("No competitions")).toBeVisible();
    }
  });

  test("competition detail", async ({ page }) => {
    await page.goto("/competitions");
    const link = page.locator('a[href^="/competitions/"]').first();
    const hasCompetitions = (await link.count()) > 0;
    test.skip(!hasCompetitions, "no competitions available");

    await link.click();
    await expect(page.getByText("Leaderboard").first()).toBeVisible();
    await expect(page.getByText("Submit").first()).toBeVisible();
  });

  test("competition leaderboard", async ({ page }) => {
    await page.goto("/competitions");
    const link = page.locator('a[href^="/competitions/"][href$="/leaderboard"]').first();
    const hasCompetitions = (await link.count()) > 0;
    test.skip(!hasCompetitions, "no competitions available");

    await link.click();
    await expect(page.getByText("Leaderboard").first()).toBeVisible();

    const table = page.locator("table");
    const noSubmissions = page.getByText("No submissions yet");
    await expect(table.or(noSubmissions).first()).toBeVisible();
  });

  test("competition submit", async ({ page }) => {
    await page.goto("/competitions");
    const link = page.locator('a[href^="/competitions/"][href$="/submit"]').first();
    const hasCompetitions = (await link.count()) > 0;
    test.skip(!hasCompetitions, "no competitions available");

    await link.click();
    await expect(page.getByText("Upload Predictions")).toBeVisible();
    await expect(page.getByText("Submission guidelines")).toBeVisible();
  });

  test("competition history", async ({ page }) => {
    await page.goto("/competitions");

    // Discover a slug from the listing
    const overviewLink = page.locator('a[href^="/competitions/"]').first();
    const hasCompetitions = (await overviewLink.count()) > 0;
    test.skip(!hasCompetitions, "no competitions available");

    const href = await overviewLink.getAttribute("href");
    const slug = href?.split("/competitions/")[1]?.split("/")[0];
    test.skip(!slug, "could not extract competition slug");

    await page.goto(`/competitions/${slug}/history`);
    await expect(page.getByText("History").first()).toBeVisible();
  });

  test("datasets listing", async ({ page }) => {
    await page.goto("/datasets");
    await expect(page.locator("main").getByText("Datasets")).toBeVisible();

    const cards = page.locator('a[href^="/datasets/"]');
    const count = await cards.count();
    if (count > 0) {
      await expect(cards.first()).toBeVisible();
    } else {
      await expect(page.getByText("No datasets")).toBeVisible();
    }
  });

  test("dataset detail", async ({ page }) => {
    await page.goto("/datasets");
    const link = page.locator('a[href^="/datasets/"]').first();
    const hasDatasets = (await link.count()) > 0;
    test.skip(!hasDatasets, "no datasets available");

    await link.click();
    await expect(page.locator("h1, h2").first()).toBeVisible();
  });

  test("rankings", async ({ page }) => {
    await page.goto("/rankings");
    await expect(page.locator("main").getByText("Rankings")).toBeVisible();
  });

  test("onboarding", async ({ page }) => {
    await page.goto("/onboarding");
    await expect(page.getByText("Welcome to MedForge")).toBeVisible();
    await expect(page.getByText("Get Started")).toBeVisible();
  });

  test("settings", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("main").getByText("Settings")).toBeVisible();
  });

  test("settings profile sub-route", async ({ page }) => {
    await page.goto("/settings/profile");
    await expect(page.locator("main").getByText("Settings")).toBeVisible();
  });

  test("settings account sub-route", async ({ page }) => {
    await page.goto("/settings/account");
    await expect(page.locator("main").getByText("Settings")).toBeVisible();
  });

  test("settings appearance sub-route", async ({ page }) => {
    await page.goto("/settings/appearance");
    await expect(page.locator("main").getByText("Settings")).toBeVisible();
  });

  test("admin redirects to /admin/users", async ({ page }) => {
    await page.goto("/admin");
    await page.waitForURL("**/admin/users");
    await expect(page.getByRole("heading", { name: "User Management" })).toBeVisible();
  });

  test("admin users", async ({ page }) => {
    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: "User Management" })).toBeVisible();
  });

  test("admin sessions", async ({ page }) => {
    await page.goto("/admin/sessions");
    await expect(page.getByRole("heading", { name: "Session Monitoring" })).toBeVisible();
  });

  test("admin competitions", async ({ page }) => {
    await page.goto("/admin/competitions");
    await expect(page.getByText("Competition Management")).toBeVisible();
  });

  test("logout invalidates the session", async ({ page }) => {
    const apiBase = resolveApiBaseURL();

    // Verify authenticated before logout
    const meBefore = await page.request.get(`${apiBase}/api/v2/me`);
    expect(meBefore.ok()).toBeTruthy();

    // Perform logout via API subdomain
    const res = await page.request.post(`${apiBase}/api/v2/auth/logout`, { data: {} });
    expect(res.ok()).toBeTruthy();

    // Same token should now be rejected
    const meAfter = await page.request.get(`${apiBase}/api/v2/me`);
    expect(meAfter.ok()).toBeFalsy();
    expect(meAfter.status()).toBe(401);
  });
});
