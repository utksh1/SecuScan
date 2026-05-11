import { test, expect } from '@playwright/test'

test('landing renders app shell', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('body')).toContainText(/SecuScan|LOGIN|DASHBOARD/i)
})
