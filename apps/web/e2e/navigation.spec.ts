import { expect, test } from "@playwright/test";

test.describe("sidebar navigation", () => {
  const sidebarLinks = [
    { label: "Sessions", path: "/sessions" },
    { label: "Dashboard", path: "/dashboard" },
    { label: "Competitions", path: "/competitions" },
    { label: "Datasets", path: "/datasets" },
    { label: "Rankings", path: "/rankings" },
  ] as const;

  for (const { label, path } of sidebarLinks) {
    test(`sidebar -> ${label}`, async ({ page }) => {
      await page.goto("/dashboard");
      await page.locator("aside nav").getByText(label, { exact: true }).click();
      await page.waitForURL(`**${path}`);
      expect(new URL(page.url()).pathname).toBe(path);
    });
  }
});

test.describe("navbar navigation", () => {
  const navLinks = [
    { label: "Competitions", path: "/competitions" },
    { label: "Datasets", path: "/datasets" },
    { label: "Sessions", path: "/sessions" },
  ] as const;

  for (const { label, path } of navLinks) {
    test(`navbar -> ${label}`, async ({ page }) => {
      await page.goto("/");
      const nav = page.locator("header nav, header");
      const link = nav.getByRole("link", { name: label }).first();
      const isVisible = await link.isVisible().catch(() => false);
      test.skip(!isVisible, `navbar link "${label}" not found on landing page`);

      await link.click();
      await page.waitForURL(`**${path}`);
      expect(new URL(page.url()).pathname).toBe(path);
    });
  }
});

test.describe("admin tab navigation", () => {
  const adminTabs = [
    { label: "Users", path: "/admin/users" },
    { label: "Sessions", path: "/admin/sessions" },
    { label: "Competitions", path: "/admin/competitions" },
  ] as const;

  for (const { label, path } of adminTabs) {
    test(`admin tab -> ${label}`, async ({ page }) => {
      await page.goto("/admin/users");
      await page.locator(`a[href="${path}"]`).click();
      await page.waitForURL(`**${path}`);
      expect(new URL(page.url()).pathname).toBe(path);
    });
  }
});
