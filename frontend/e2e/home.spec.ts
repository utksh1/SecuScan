import { test, expect } from '@playwright/test';

test('has title and displays sidebar', async ({ page }) => {
  // Navigate to the local frontend server
  await page.goto('/');

  // Expect the title to contain SecuScan
  await expect(page).toHaveTitle(/SecuScan/i);

  // Expect the sidebar to be visible (look for Dashboard link)
  const dashboardLink = page.getByRole('link', { name: /Dashboard/i });
  await expect(dashboardLink).toBeVisible();

  // Look for New Scan button or link
  const scanLink = page.getByRole('link', { name: /New Scan/i });
  await expect(scanLink).toBeVisible();
});
