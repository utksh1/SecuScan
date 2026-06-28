import { test, expect } from '@playwright/test';

test.describe('Mobile navigation regression (overlap guard)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({
      width: 390,
      height: 844,
    });
    await page.route('**/api/v1/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      });
    });

    await page.route('**/api/v1/dashboard/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_scans: 0,
          active_workflows: 0,
          recent_findings: [],
        }),
      });
    });

    await page.goto('/');

    await page.evaluate(() => {
      localStorage.setItem(
        'secuscan_api_key',
        '6abeafd82cdb0eebea98dc3817b0bb5f9f8773f60402bccad9eaad7870ae8f58'
      );
    });

    await page.goto('/dashboard', {
      waitUntil: 'domcontentloaded',
    });
  });

  test('drawer opens without overlap (structural + visual regression)', async ({ page }) => {
    const menuButton = page.getByRole('button', {
      name: /toggle navigation menu/i,
    });

    await expect(menuButton).toBeVisible();
    await menuButton.click();

    const mobileNav = page
      .locator('nav')
      .filter({
        has: page.getByRole('link', { name: /dashboard/i }),
      })
      .first();

    await expect(mobileNav).toBeVisible();

    const dashboardLink = mobileNav.getByRole('link', { name: /dashboard/i });
    const settingsLink = mobileNav.getByRole('link', { name: /settings/i });

    await expect(dashboardLink).toBeVisible();
    await expect(settingsLink).toBeVisible();

    const menuBox = await menuButton.boundingBox();
    const settingsBox = await settingsLink.boundingBox();

    expect(menuBox).not.toBeNull();
    expect(settingsBox).not.toBeNull();

    expect(settingsBox!.y).toBeGreaterThan(
      menuBox!.y + menuBox!.height
    );

    await expect(mobileNav).toHaveScreenshot('mobile-nav-open.png', {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.02,
    });
  });
});