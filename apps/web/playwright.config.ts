import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL?.trim() || "http://medforge.localtest.me:18080";
const ignoreHTTPSErrors = (process.env.E2E_IGNORE_HTTPS_ERRORS ?? "true").toLowerCase() === "true";
const hostRules = process.env.E2E_CHROMIUM_HOST_RULES?.trim();

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
