import { test, expect } from "@playwright/test";

test.describe("Settings persistence", () => {

  test("theme persists after reload", async ({ page }) => {
    await page.goto("/");

    await page.evaluate(() => {
      localStorage.setItem(
        "secuscan_api_key",
        "6abeafd82cdb0eebea98dc3817b0bb5f9f8773f60402bccad9eaad7870ae8f58"
      );
    });

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
    await page.goto("/");

    await page.evaluate(() => {
      localStorage.setItem("secuscan_api_key",  "6abeafd82cdb0eebea98dc3817b0bb5f9f8773f60402bccad9eaad7870ae8f58");
    });

    await page.goto("/settings");

    const resetButton = page.getByRole("button", {
      name: /reset to system default/i,
    });

    await expect(resetButton).toBeVisible();


  });

});
