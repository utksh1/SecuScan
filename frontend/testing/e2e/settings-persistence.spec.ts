import { test, expect, type Page } from "@playwright/test";

async function mockAuthenticatedSession(page: Page) {
  await page.route("**/api/v1/auth/session/check", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ authenticated: true }),
    })
  );

  await page.route("**/api/v1/notifications/rules", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ rules: [], total: 0 }),
    })
  );
}

test.describe("Settings persistence", () => {

  test("theme persists after reload", async ({ page }) => {
    await mockAuthenticatedSession(page);

    await page.goto("/settings");

    await page.waitForLoadState("networkidle");

    const themeSelect = page.getByLabel(/visual spectrum theme/i);

    await themeSelect.selectOption("light");

    await page.getByRole("button", {
      name: /commit_engine_changes/i,
    }).click();

    await page.reload();

    await expect(
      page.getByLabel(/visual spectrum theme/i)
    ).toHaveValue("light");
  });

  test("theme reset path is available", async ({ page }) => {
    await mockAuthenticatedSession(page);

    await page.goto("/settings");

    const resetButton = page.getByRole("button", {
      name: /reset to system default/i,
    });

    await expect(resetButton).toBeVisible();


  });

});
