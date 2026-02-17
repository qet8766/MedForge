import { defineConfig, devices } from "@playwright/test";

const domain = process.env.E2E_DOMAIN?.trim() || process.env.DOMAIN?.trim() || "";
const baseURL = process.env.E2E_BASE_URL?.trim() || (domain ? `https://medforge.${domain}` : "");
const ignoreHTTPSErrors = (process.env.E2E_IGNORE_HTTPS_ERRORS ?? "true").toLowerCase() === "true";
const hostRules = process.env.E2E_CHROMIUM_HOST_RULES?.trim();

if (!baseURL) {
  throw new Error("E2E_BASE_URL (or E2E_DOMAIN/DOMAIN) is required for remote-public e2e.");
}

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: {
    timeout: 20_000
  },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    ignoreHTTPSErrors,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: hostRules ? { args: [`--host-rules=${hostRules}`] } : undefined
      }
    }
  ]
});
