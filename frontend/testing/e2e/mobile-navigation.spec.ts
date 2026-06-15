import { test, expect } from '@playwright/test';

const API_KEY =
  '6abeafd82cdb0eebea98dc3817b0bb5f9f8773f60402bccad9eaad7870ae8f58';

test.describe('Mobile navigation regression (overlap guard)', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({
      width: 390,
      height: 844,
    });

    await page.addInitScript((key) => {
      localStorage.setItem('secuscan_api_key', key);
    }, API_KEY);

    await page.goto('/dashboard', {
      waitUntil: 'domcontentloaded',
    });
  });

  test('drawer opens without overlap (structural + visual regression)', async ({
    page,
  }) => {
    const menuButton = page.getByRole('button', {
      name: /toggle navigation menu/i,
    });

    await expect(menuButton).toBeVisible();

    await menuButton.click();

    // Find only the mobile navigation drawer
    const mobileNav = page
      .locator('nav')
      .filter({
        has: page.getByRole('link', { name: /dashboard/i }),
      })
      .first();

    await expect(mobileNav).toBeVisible();

    const dashboardLink = mobileNav
      .getByRole('link', { name: /dashboard/i })
      .first();

    const settingsLink = mobileNav
      .getByRole('link', { name: /settings/i })
      .first();

    await expect(dashboardLink).toBeVisible();
    await expect(settingsLink).toBeVisible();

    // Core overlap regression check
    const menuBox = await menuButton.boundingBox();
    const settingsBox = await settingsLink.boundingBox();

    expect(menuBox).not.toBeNull();
    expect(settingsBox).not.toBeNull();

    expect(settingsBox!.y).toBeGreaterThan(
      menuBox!.y + menuBox!.height
    );

    // Stable visual regression snapshot
    await expect(mobileNav).toHaveScreenshot(
      'mobile-nav-open.png',
      {
        animations: 'disabled',
        caret: 'hide',
        maxDiffPixelRatio: 0.02,
      }
    );
  });

  test('mobile nav does not block main content', async ({ page }) => {
    const menuButton = page.getByRole('button', {
      name: /toggle navigation menu/i,
    });

    await expect(menuButton).toBeVisible();

    await menuButton.click();

    const main = page
      .locator('main')
      .filter({
        hasText: /dashboard|workspace|secuscan/i,
      })
      .first();

    await expect(main).toBeVisible();

    const box = await main.boundingBox();

    expect(box).not.toBeNull();

    // Main content should remain rendered and visible
    expect(box!.width).toBeGreaterThan(100);
    expect(box!.height).toBeGreaterThan(100);
    expect(box!.x).toBeGreaterThanOrEqual(0);
  });
});