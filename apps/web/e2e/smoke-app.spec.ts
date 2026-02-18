import { expect, test } from "@playwright/test";

test.describe("authenticated app pages", () => {
  test("dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Welcome back")).toBeVisible();
    await expect(page.getByText("Competitions").first()).toBeVisible();
    await expect(page.getByText("Session Status")).toBeVisible();
    await expect(page.getByText("Quick Actions")).toBeVisible();
  });

  test("sessions", async ({ page }) => {
    await page.goto("/sessions");
    await expect(page.locator("h1")).toContainText("Sessions");
    await expect(page.getByText("Session History")).toBeVisible();
  });

  test("competitions listing", async ({ page }) => {
    await page.goto("/competitions");
    await expect(page.getByText("Competitions").first()).toBeVisible();

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
    await expect(page.getByText("Datasets").first()).toBeVisible();

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
    await expect(page.getByText("Rankings").first()).toBeVisible();
  });

  test("onboarding", async ({ page }) => {
    await page.goto("/onboarding");
    await expect(page.getByText("Welcome to MedForge")).toBeVisible();
    await expect(page.getByText("Get Started")).toBeVisible();
  });

  test("settings", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText("Settings").first()).toBeVisible();
  });

  test("settings profile sub-route", async ({ page }) => {
    await page.goto("/settings/profile");
    await expect(page.getByText("Settings").first()).toBeVisible();
  });

  test("settings account sub-route", async ({ page }) => {
    await page.goto("/settings/account");
    await expect(page.getByText("Settings").first()).toBeVisible();
  });

  test("settings appearance sub-route", async ({ page }) => {
    await page.goto("/settings/appearance");
    await expect(page.getByText("Settings").first()).toBeVisible();
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
    await page.goto("/sessions");
    await page.waitForURL(/\/sessions/);

    // Perform logout
    const res = await page.request.post("/api/v2/auth/logout", { data: {} });
    expect(res.ok()).toBeTruthy();

    // Protected route should now redirect to login
    await page.goto("/sessions");
    await page.waitForURL(/\/login/, { timeout: 5_000 });
  });
});
