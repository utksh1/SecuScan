import { test, expect } from '@playwright/test';

test('has title and displays sidebar', async ({ page }) => {
  await page.route('**/api/v1/auth/session/check', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ authenticated: true }),
    })
  );
  await page.route('**/api/v1/dashboard/summary', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    })
  );

  await page.goto('/');

  await expect(page).toHaveTitle(/SecuScan/i);

  const dashboardLink = page.getByRole('link', { name: /Dashboard/i });
  await expect(dashboardLink).toBeVisible();

  const toolkitLink = page.getByRole('link', { name: /Toolkit/i });
  await expect(toolkitLink).toBeVisible();
});
