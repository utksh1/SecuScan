import { expect, test } from '@playwright/test';

const pages = [
    { name: 'dashboard', path: '/' },
    { name: 'scans', path: '/scans' },
    { name: 'reports', path: '/reports' },
    { name: 'toolkit', path: '/toolkit' },
    { name: 'settings', path: '/settings' },
];

const viewports = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
];

for (const appPage of pages) {
    for (const viewport of viewports) {
        test(`${appPage.name} light mode ${viewport.name}`, async ({ page }) => {
            await page.setViewportSize(viewport);
            await page.emulateMedia({ colorScheme: 'light' });
            await page.goto(appPage.path);
            await page.waitForLoadState('networkidle');

            await expect(page).toHaveScreenshot(
                `${appPage.name}-light-${viewport.name}.png`,
                {
                    fullPage: true,
                    animations: 'disabled',
                    maxDiffPixelRatio: 0.01,
                }
            );
        });

        test(`${appPage.name} dark mode ${viewport.name}`, async ({ page }) => {
            await page.setViewportSize(viewport);
            await page.emulateMedia({ colorScheme: 'dark' });
            await page.goto(appPage.path);
            await page.waitForLoadState('networkidle');

            await expect(page).toHaveScreenshot(
                `${appPage.name}-dark-${viewport.name}.png`,
                {
                    fullPage: true,
                    animations: 'disabled',
                    maxDiffPixelRatio: 0.01,
                }
            );
        });
    }
}