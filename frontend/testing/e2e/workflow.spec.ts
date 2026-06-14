import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const API_KEY = '6abeafd82cdb0eebea98dc3817b0bb5f9f8773f60402bccad9eaad7870ae8f58';

const MOCK_WORKFLOWS = [
  {
    id: 'wf-001',
    name: 'Daily DNS Scan',
    schedule_seconds: 86400,
    enabled: true,
    steps: [{ plugin_id: 'dns_recon', inputs: { target: 'example.com' } }],
    last_run_at: new Date(Date.now() - 3600000).toISOString(),
    queued_task_ids: [],
    created_at: new Date().toISOString(),
  },
];

const MOCK_CREATED_WORKFLOW = {
  id: 'wf-002',
  name: 'Nightly Port Scan',
  schedule_seconds: 43200,
  enabled: true,
  steps: [{ plugin_id: 'port_scanner', inputs: { target: '10.0.0.1' } }],
  last_run_at: null,
  queued_task_ids: [],
  created_at: new Date().toISOString(),
};

const MOCK_RUN_RESPONSE = {
  queued_task_ids: ['task-001', 'task-002'],
};

async function setupMocks(page: import('@playwright/test').Page) {
  await page.route(`${BASE}/api/v1/workflows`, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workflows: MOCK_WORKFLOWS, total: 1 }),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_CREATED_WORKFLOW),
      });
    } else {
      await route.fulfill({ status: 404 });
    }
  });

  await page.route(`${BASE}/api/v1/workflows/*/run`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RUN_RESPONSE),
    });
    await page.route(`${BASE}/api/v1/workflows`, async (innerRoute) => {
      const updated = MOCK_WORKFLOWS.map(w => ({
        ...w,
        queued_task_ids: ['task-001', 'task-002'],
        last_run_at: new Date().toISOString(),
      }));
      await innerRoute.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workflows: updated, total: 1 }),
      });
    });
  });

  await page.route(`${BASE}/api/v1/workflows/*`, async (route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted: true }),
      });
      await page.route(`${BASE}/api/v1/workflows`, async (innerRoute) => {
        await innerRoute.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ workflows: [], total: 0 }),
        });
      });
    } else {
      await route.fulfill({ status: 404 });
    }
  });
}

test.describe('Workflow lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate((key) => {
      localStorage.setItem('secuscan_api_key', key);
    }, API_KEY);
  });

  test('displays existing workflows', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/workflows');
    await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible();
    await expect(page.getByText('Daily DNS Scan')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Enabled')).toBeVisible();
  });

  test('creates a new workflow via the create sheet', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/workflows');
    await page.getByRole('button', { name: /new workflow/i }).click();
    await expect(page.getByRole('heading', { name: /new workflow/i })).toBeVisible();
    await page.getByPlaceholder('My Workflow').fill('Nightly Port Scan');
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page.getByText('Nightly Port Scan')).toBeVisible({ timeout: 10000 });
  });

  test('runs a workflow and shows queued tasks', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/workflows');
    await expect(page.getByText('Daily DNS Scan')).toBeVisible({ timeout: 10000 });
    await page.getByTitle('Run now').click();
    await expect(page.getByText('task-001')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('task-002')).toBeVisible();
  });

  test('deletes a workflow and removes it from the grid', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/workflows');
    await expect(page.getByText('Daily DNS Scan')).toBeVisible({ timeout: 10000 });
    await page.getByTitle('Delete').click();
    await expect(page.getByRole('heading', { name: /delete workflow/i })).toBeVisible();
    await page.getByRole('button', { name: 'Delete' }).click();
    await expect(page.getByText('No Workflows')).toBeVisible({ timeout: 10000 });
  });

  test('full lifecycle: create, run, and delete a workflow', async ({ page }) => {
    await setupMocks(page);
    await page.goto('/workflows');
    await expect(page.getByText('Daily DNS Scan')).toBeVisible({ timeout: 10000 });
    await page.getByRole('button', { name: /new workflow/i }).click();
    await page.getByPlaceholder('My Workflow').fill('Nightly Port Scan');
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page.getByText('Nightly Port Scan')).toBeVisible({ timeout: 10000 });
    await page.getByTitle('Run now').first().click();
    await page.getByTitle('Delete').first().click();
    await page.getByRole('button', { name: 'Delete' }).click();
    await expect(page.getByText('No Workflows')).toBeVisible({ timeout: 10000 });
  });
});
