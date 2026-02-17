import { test as setup } from "@playwright/test";

import { AUTH_STATE_PATH, ensureSignedIn, resolveCredentials } from "./helpers";

setup("authenticate", async ({ page }) => {
  const { email, password } = resolveCredentials();
  await ensureSignedIn(page, email, password);
  await page.context().storageState({ path: AUTH_STATE_PATH });
});
