import { test, expect } from "@playwright/test";

const BASE = "http://127.0.0.1:5173";

const MOCK_PLUGINS_RESPONSE = {
  plugins: [{
    id: "dns_recon", name: "DNS Recon",
    description: "Perform DNS reconnaissance on a target domain.",
    category: "recon", safety_level: "passive", enabled: true, icon: "dns",
    requires_consent: false, consent_message: null,
    availability: { runnable: true, missing_binaries: [], status: "ok", guidance: null },
  }],
  total: 1,
};

const MOCK_PLUGIN_SCHEMA = {
  id: "dns_recon", name: "DNS Recon",
  description: "Perform DNS reconnaissance on a target domain.",
  fields: [{
    id: "target", label: "Target Domain", type: "string",
    required: true, placeholder: "example.com", help: "The domain to scan.",
  }],
  presets: { quick: { target: "" } },
  safety: { level: "passive" },
};

const MOCK_START_TASK_RESPONSE = {
  task_id: "abcd1234-0000-0000-0000-000000000001", status: "queued",
  created_at: new Date().toISOString(),
  stream_url: `${BASE}/api/v1/task/abcd1234-0000-0000-0000-000000000001/stream`,
};

const MOCK_TASK_STATUS = {
  task_id: "abcd1234-0000-0000-0000-000000000001", plugin_id: "dns_recon",
  tool: "DNS Recon", target: "example.com", status: "completed",
  created_at: new Date().toISOString(), started_at: new Date().toISOString(),
  completed_at: new Date().toISOString(), duration_seconds: 5,
  exit_code: 0, error_message: null,
  inputs: { target: "example.com" }, preset: "quick",
};

const MOCK_TASK_RESULT = {
  task_id: "abcd1234-0000-0000-0000-000000000001", plugin_id: "dns_recon",
  tool: "DNS Recon", target: "example.com",
  timestamp: new Date().toISOString(), duration_seconds: 5, status: "completed",
  summary: ["DNS scan completed for example.com.", "2 findings identified."],
  severity_counts: { info: 2 },
  findings: [
    { title: "A Record Found", category: "dns", severity: "info", target: "example.com", description: "The domain resolves to 93.184.216.34." },
    { title: "MX Record Found", category: "dns", severity: "info", target: "example.com", description: "Mail exchanger record detected." },
  ],
  structured: {
    total_count: 2,
    findings: [
      { title: "A Record Found", category: "dns", severity: "info", target: "example.com", description: "The domain resolves to 93.184.216.34." },
      { title: "MX Record Found", category: "dns", severity: "info", target: "example.com", description: "Mail exchanger record detected." },
    ],
  },
  raw_output: "DNS recon complete.\nFound A record: 93.184.216.34\nFound MX record.",
  command_used: "dnsrecon -d example.com",
  errors: [],
};

async function setupMocks(page) {
  await page.route(`**/api/v1/auth/session/check`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ authenticated: true }) })
  );
  await page.route(`**/api/v1/health`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) })
  );
  await page.route(`**/api/v1/dashboard/summary`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) })
  );
  await page.route(`**/api/v1/settings`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) })
  );
  await page.route(`**/api/v1/target-policies`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
  );
  await page.route(`**/api/v1/credential-profiles`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
  );
  await page.route(`**/api/v1/session-profiles`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
  );
  await page.route(`**/api/v1/plugins`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_PLUGINS_RESPONSE) })
  );
  await page.route(`**/api/v1/plugin/dns_recon/schema`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_PLUGIN_SCHEMA) })
  );
  await page.route(`**/api/v1/task/start`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_START_TASK_RESPONSE) })
  );
  await page.route(`**/api/v1/task/abcd1234-0000-0000-0000-000000000001/status`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_TASK_STATUS) })
  );
  await page.route(`**/api/v1/task/abcd1234-0000-0000-0000-000000000001/result`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_TASK_RESULT) })
  );
  await page.route(`**/api/v1/task/abcd1234-0000-0000-0000-000000000001/stream`, (route) =>
    route.fulfill({ status: 200, headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" }, body: "" })
  );
}

test.describe("Full scan workflow", () => {
  test("Step 1 - Open scanner catalog and see tool cards", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit");
    await expect(page.getByRole("heading", { name: /tactical/i })).toBeVisible({ timeout: 10000 });
    await page.getByRole("tab", { name: /recon tools/i }).click();
    await expect(page.getByRole("button", { name: /dns recon/i })).toBeVisible({ timeout: 10000 });
  });

  test("Step 2 - Select a scanner and see its config page", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit");
    await page.getByRole("tab", { name: /recon tools/i }).click();
    await page.getByRole("button", { name: /dns recon/i }).click();
    await expect(page).toHaveURL(/\/toolkit\/dns_recon/);
    await expect(page.getByRole("heading", { name: /dns recon/i })).toBeVisible();
  });

  test("Step 3 - Fill dynamic inputs on config page", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit/dns_recon");
    const targetInput = page.getByPlaceholder("example.com");
    await expect(targetInput).toBeVisible();
    await targetInput.fill("example.com");
    await expect(targetInput).toHaveValue("example.com");
  });

  test("Step 4 - No consent required INITIATE_SCAN button is enabled", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit/dns_recon");
    await expect(page.getByRole("checkbox")).not.toBeVisible();
    await page.getByPlaceholder("example.com").fill("example.com");
    const startButton = page.getByRole("button", { name: /initiate_scan/i });
    await expect(startButton).toBeVisible();
    await expect(startButton).not.toBeDisabled();
  });

  test("Step 5 - Queue the scan and navigate to task details", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit/dns_recon");
    await page.getByPlaceholder("example.com").fill("example.com");
    await page.getByRole("button", { name: /initiate_scan/i }).click();
    await expect(page).toHaveURL(/\/task\/abcd1234/);
  });

  test("Step 6 - Task details page shows status and target", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/task/abcd1234-0000-0000-0000-000000000001");
    await expect(page.getByText(/completed/i).first()).toBeVisible();
    await expect(page.getByText("example.com").first()).toBeVisible();
  });

  test("Step 7 - Report export actions are available after completion", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/task/abcd1234-0000-0000-0000-000000000001");
    await expect(page.getByRole("button", { name: /html_export/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /csv_export/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /pdf_report/i })).toBeVisible();
  });

  test("Full journey - end-to-end from catalog to report export", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/toolkit");
    await expect(page.getByRole("heading", { name: /tactical/i })).toBeVisible({ timeout: 10000 });
    await page.getByRole("tab", { name: /recon tools/i }).click();
    await page.getByRole("button", { name: /dns recon/i }).click();
    await expect(page).toHaveURL(/\/toolkit\/dns_recon/);
    await page.getByPlaceholder("example.com").fill("example.com");
    await page.getByRole("button", { name: /initiate_scan/i }).click();
    await expect(page).toHaveURL(/\/task\/abcd1234/);
    await expect(page.getByText(/completed/i).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /pdf_report/i })).toBeVisible();
  });
});

test.describe("Scan workflow - consent required", () => {
  test("Consent checkbox is shown and blocks scan until checked", async ({ page }) => {
    await page.route(`**/api/v1/auth/session/check`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ authenticated: true }) })
    );
    await page.route(`**/api/v1/health`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) })
    );
    await page.route(`**/api/v1/dashboard/summary`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) })
    );
    await page.route(`**/api/v1/settings`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) })
    );
    await page.route(`**/api/v1/target-policies`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
    );
    await page.route(`**/api/v1/credential-profiles`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
    );
    await page.route(`**/api/v1/session-profiles`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0 }) })
    );
    await page.route(`**/api/v1/plugins`, (route) =>
      route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          plugins: [{
            id: "port_scanner", name: "Port Scanner",
            description: "Scan open ports.", category: "recon",
            safety_level: "intrusive", enabled: true, icon: "radar",
            requires_consent: true,
            consent_message: "You must have explicit authorization to scan this target.",
            availability: { runnable: true, missing_binaries: [], status: "ok", guidance: null },
          }],
          total: 1,
        }),
      })
    );
    await page.route(`**/api/v1/plugin/port_scanner/schema`, (route) =>
      route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          id: "port_scanner", name: "Port Scanner", description: "Scan open ports.",
          fields: [{ id: "target", label: "Target Host", type: "string", required: true, placeholder: "192.168.1.1", help: "IP or hostname." }],
          presets: {}, safety: { level: "intrusive" },
        }),
      })
    );
    await page.goto("/toolkit/port_scanner");
    const consentCheckbox = page.getByRole("checkbox");
    await expect(consentCheckbox).toBeVisible();
    await expect(consentCheckbox).not.toBeChecked();
    await page.getByPlaceholder("192.168.1.1").fill("192.168.1.1");
    await consentCheckbox.check();
    await expect(consentCheckbox).toBeChecked();
    await expect(page.getByRole("button", { name: /initiate_scan/i })).not.toBeDisabled();
  });
});
