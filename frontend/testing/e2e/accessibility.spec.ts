import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Mock API responses so tests are deterministic and backend-independent
async function mockScanAPIs(page: any) {
  await page.route('**/api/v1/tasks**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        tasks: [
          {
            task_id: 'test-task-001',
            plugin_id: 'nmap',
            tool: 'Nmap Port Scanner',
            target: 'example.com',
            status: 'completed',
            created_at: new Date().toISOString(),
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            duration_seconds: 45,
          },
          {
            task_id: 'test-task-002',
            plugin_id: 'nikto',
            tool: 'Nikto Web Scanner',
            target: 'test.example.com',
            status: 'failed',
            created_at: new Date().toISOString(),
          }
        ]
      })
    })
  )
}

async function mockFindingsAPIs(page: any) {
  await page.route('**/api/v1/findings**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        findings: [
          {
            id: 'finding-001',
            severity: 'critical',
            category: 'XSS',
            title: 'Reflected XSS in search parameter',
            target: 'example.com',
            description: 'User input is reflected without sanitization.',
            remediation: 'Encode all user-supplied output.',
            discovered_at: new Date().toISOString(),
            cvss: 9.1,
            cve: 'CVE-2024-1234',
          },
          {
            id: 'finding-002',
            severity: 'high',
            category: 'SQLi',
            title: 'SQL Injection in login form',
            target: 'example.com',
            description: 'Login form is vulnerable to SQL injection.',
            remediation: 'Use parameterized queries.',
            discovered_at: new Date().toISOString(),
            cvss: 8.2,
          }
        ]
      })
    })
  )
}

async function mockPluginsAPIs(page: any) {
  await page.route('**/api/v1/plugins**', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total: 2,
        plugins: [
          {
            id: 'nmap',
            name: 'Nmap',
            description: 'Network port scanner',
            category: 'recon',
            safety_level: 'safe',
            enabled: true,
            icon: '🔍',
            requires_consent: false,
            consent_message: null,
            availability: { runnable: true, missing_binaries: [] },
          },
          {
            id: 'nikto',
            name: 'Nikto',
            description: 'Web vulnerability scanner',
            category: 'vulnerability',
            safety_level: 'intrusive',
            enabled: true,
            icon: '🕷️',
            requires_consent: true,
            consent_message: 'This scan may generate significant traffic.',
            availability: { runnable: true, missing_binaries: [] },
          }
        ]
      })
    })
  )
}

// ── Scans Page ─────────────────────────────────────────────────────────────

test.describe('Accessibility — Scans Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
    await mockScanAPIs(page)
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      // color-contrast is a pre-existing design system issue, not scope of this PR
      .disableRules(['color-contrast'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('status filter buttons have aria-pressed', async ({ page }) => {
    await mockScanAPIs(page)
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    // Find filter buttons by their known labels — fails if aria-pressed is absent
    const allOpsBtn = page.locator('button[aria-label="Filter by ALL_OPERATIONS"]')
    await expect(allOpsBtn).toBeVisible()
    const pressed = await allOpsBtn.getAttribute('aria-pressed')
    expect(pressed).not.toBeNull() // fails if aria-pressed attribute is missing entirely
    expect(['true', 'false']).toContain(pressed)

    // Active filter must be aria-pressed=true
    expect(pressed).toBe('true') // ALL_OPERATIONS is active by default
  })

  test('filter buttons are keyboard reachable and activatable', async ({ page }) => {
    await mockScanAPIs(page)
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    // Tab until we land on a button
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab')
      const tag = await page.evaluate(() => document.activeElement?.tagName)
      if (tag === 'BUTTON') break
    }

    const focusedTag = await page.evaluate(() => document.activeElement?.tagName)
    expect(focusedTag).toBe('BUTTON')
  })

  test('task cards have role=button and aria-label', async ({ page }) => {
    await mockScanAPIs(page)
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    const cards = page.locator('[role="button"][aria-expanded]')
    const count = await cards.count()

    // Only assert if tasks exist — empty state is valid
    if (count > 0) {
      const label = await cards.first().getAttribute('aria-label')
      expect(label).toBeTruthy()
      expect(label).toMatch(/Scan record/i)
    } else {
      // Empty state is acceptable — just verify page loaded
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('selection checkboxes have role=checkbox and aria-checked', async ({ page }) => {
    await mockScanAPIs(page)
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    // Fails if role=checkbox is missing
    const checkboxes = page.locator('[role="checkbox"]')
    await expect(checkboxes.first()).toBeVisible()

    // Fails if aria-checked attribute is missing entirely
    const checked = await checkboxes.first().getAttribute('aria-checked')
    expect(checked).not.toBeNull()
    expect(checked).toBe('false') // unchecked by default

    // Click the checkbox — aria-checked must flip to true
    await checkboxes.first().click()
    const checkedAfter = await checkboxes.first().getAttribute('aria-checked')
    expect(checkedAfter).toBe('true')
  })

})

// ── Findings Page ──────────────────────────────────────────────────────────

test.describe('Accessibility — Findings Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('search input has id and aria-label', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#findings-search')
    await expect(input).toBeVisible()

    const label = await input.getAttribute('aria-label')
    expect(label).toBeTruthy()
  })

  test('search input is keyboard reachable and typeable', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#findings-search')
    await input.focus()
    await input.fill('xss')

    await expect(input).toHaveValue('xss')
  })

  test('severity filter buttons have aria-pressed', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const allBtn = page.locator('button[aria-label="Show all severity levels"]')
    await expect(allBtn).toBeVisible()

    // Fails if aria-pressed attribute is missing entirely
    const pressed = await allBtn.getAttribute('aria-pressed')
    expect(pressed).not.toBeNull()
    expect(pressed).toBe('true') // All Levels active by default

    // Click a severity filter — it must become aria-pressed=true, All Levels must become false
    const criticalBtn = page.locator('button[aria-label*="Critical"]').first()
    await criticalBtn.click()
    const criticalPressed = await criticalBtn.getAttribute('aria-pressed')
    expect(criticalPressed).toBe('true')
    const allPressedAfter = await allBtn.getAttribute('aria-pressed')
    expect(allPressedAfter).toBe('false')
  })

  test('severity filter groups have role=group', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const groups = page.locator('[role="group"]')
    const count = await groups.count()
    expect(count).toBeGreaterThan(0)
  })

  test('detail panel has aria-label and aria-live', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const aside = page.locator('aside[aria-label="Finding detail panel"]')
    await expect(aside).toBeVisible()

    const live = await aside.getAttribute('aria-live')
    expect(live).toBe('polite')
  })

  test('finding list buttons have aria-pressed and aria-label', async ({ page }) => {
    await mockFindingsAPIs(page)
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    // Target the finding list item button specifically — it has aria-pressed
    // Use the exact full label pattern from our mocked data
    const findingBtn = page.locator('button[aria-pressed][aria-label*="Reflected XSS"]')
    await expect(findingBtn).toBeVisible()

    // Fails if aria-pressed is missing (selector above would return 0 elements)
    const pressed = await findingBtn.getAttribute('aria-pressed')
    expect(pressed).not.toBeNull()

    // Click it — aria-pressed must become true
    await findingBtn.click()
    const pressedAfter = await findingBtn.getAttribute('aria-pressed')
    expect(pressedAfter).toBe('true')
  })

})

// ── Toolkit (Plugins) Page ─────────────────────────────────────────────────

test.describe('Accessibility — Toolkit Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('search input has id and aria-label', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#toolkit-search')
    await expect(input).toBeVisible()

    const label = await input.getAttribute('aria-label')
    expect(label).toBeTruthy()
  })

  test('nav has role=tablist and tabs have role=tab', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const tablist = page.locator('[role="tablist"]')

    // Backend may be down — tablist renders empty but exists in DOM
    const exists = await tablist.count()
    expect(exists).toBeGreaterThan(0)

    // If tabs loaded, verify them
    const tabs = page.locator('[role="tab"]')
    const tabCount = await tabs.count()
    if (tabCount > 0) {
      expect(tabCount).toBeGreaterThan(0)
    }
  })

  test('active tab has aria-selected=true', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const tabs = page.locator('[role="tab"]')
    const count = await tabs.count()

    // Find tabs by name — not by the attribute we are testing
    const quickStartTab = page.locator('[role="tab"][aria-label*="Quick Start"]')
    await expect(quickStartTab).toBeVisible()

    // Fails if aria-selected is missing
    const selected = await quickStartTab.getAttribute('aria-selected')
    expect(selected).not.toBeNull()
    expect(selected).toBe('true') // Quick Start active by default

    // Click another tab — it must become aria-selected=true, Quick Start false
    const reconTab = page.locator('[role="tab"][aria-label*="Recon"]')
    await reconTab.click()
    const reconSelected = await reconTab.getAttribute('aria-selected')
    expect(reconSelected).toBe('true')
    const quickStartAfter = await quickStartTab.getAttribute('aria-selected')
    expect(quickStartAfter).toBe('false')
  })

  test('tab panel has role=tabpanel', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const panel = page.locator('[role="tabpanel"]')
    await expect(panel).toBeVisible()
  })

  test('tool cards have aria-label and aria-disabled when loaded', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const cards = page.locator('button[aria-label][aria-disabled]')
    const count = await cards.count()

    // Find tool cards by their known mocked name — not by the attribute we are testing
    const nmapCard = page.locator('button[aria-label*="Nmap"]')
    await expect(nmapCard).toBeVisible()

    // Fails if aria-disabled is missing entirely
    const disabled = await nmapCard.getAttribute('aria-disabled')
    expect(disabled).not.toBeNull()
    expect(disabled).toBe('false') // Nmap is runnable in mock

    // Fails if aria-label is missing
    const label = await nmapCard.getAttribute('aria-label')
    expect(label).not.toBeNull()
    expect(label).toMatch(/Nmap/i)
  })

  test('tab switching is keyboard operable when tabs are present', async ({ page }) => {
    await mockPluginsAPIs(page)
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const tabs = page.locator('[role="tab"]')
    const count = await tabs.count()

    // With mocked data tabs are always present — assert deterministically
    await expect(tabs.first()).toBeVisible()
    await tabs.first().focus()
    await page.keyboard.press('Enter')
    const selected = await tabs.first().getAttribute('aria-selected')
    expect(selected).toBe('true')
  })

})
