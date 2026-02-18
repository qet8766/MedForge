import fs from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { ensureSignedIn, resolveBaseURL, resolveCredentials, resolveDomain } from "./helpers";

async function waitForSessionRouteReady(sessionPage: Page, sessionOrigin: string): Promise<void> {
  let lastStatus = 0;
  let lastError = "";
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await sessionPage.goto(sessionOrigin, { waitUntil: "domcontentloaded" });
      lastStatus = response?.status() ?? 0;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
      await sessionPage.waitForTimeout(1_000);
      continue;
    }
    const hasMissingUpstream = (await sessionPage.getByText("Session upstream missing").count()) > 0;
    if (lastStatus === 200 && !hasMissingUpstream) {
      return;
    }
    await sessionPage.waitForTimeout(1_000);
  }
  throw new Error(`Session wildcard route not ready (last_status=${lastStatus}, last_error=${lastError}).`);
}

test("login -> create session -> open wildcard host -> websocket -> stop", async ({ page }) => {
  const baseURL = resolveBaseURL();
  const domain = resolveDomain(baseURL);
  const { email, password } = resolveCredentials();

  await ensureSignedIn(page, email, password);

  await page.goto("/sessions");
  await page.getByTestId("session-create").click();
  await page.getByTestId("session-create-confirm").click();
  await page.getByTestId("session-current").waitFor({ state: "visible", timeout: 20_000 });

  const slugRaw = await page.getByTestId("session-slug").textContent();
  const slug = slugRaw?.trim() || "";
  expect(slug).toMatch(/^[a-z0-9]{8}$/);

  const base = new URL(baseURL);
  const sessionOrigin = `${base.protocol}//s-${slug}.external.${domain}${base.port ? `:${base.port}` : ""}`;

  const sessionPage = await page.context().newPage();
  const websocketState = {
    attempted: 0,
    withFrames: 0,
  };
  sessionPage.on("websocket", (ws) => {
    websocketState.attempted += 1;
    let countedFrames = false;
    ws.on("framereceived", () => {
      if (!countedFrames) {
        websocketState.withFrames += 1;
        countedFrames = true;
      }
    });
    ws.on("framesent", () => {
      if (!countedFrames) {
        websocketState.withFrames += 1;
        countedFrames = true;
      }
    });
  });

  await waitForSessionRouteReady(sessionPage, sessionOrigin);
  await expect.poll(() => websocketState.withFrames, { timeout: 30_000 }).toBeGreaterThan(0);
  await sessionPage.close();

  await page.getByTestId("session-stop").click();
  await page.getByTestId("session-stop-confirm").click();
  await expect(page.getByText("Session stop requested.")).toBeVisible({ timeout: 10_000 });

  const resultFile = process.env.E2E_RESULT_FILE?.trim();
  if (resultFile) {
    const result = {
      base_url: baseURL,
      session_url: sessionOrigin,
      slug,
      websocket_attempted: websocketState.attempted,
      websocket_with_frames: websocketState.withFrames,
      timestamp: new Date().toISOString(),
    };
    fs.writeFileSync(resultFile, JSON.stringify(result, null, 2), "utf8");
  }
});
