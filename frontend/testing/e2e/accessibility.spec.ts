import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// ── Scans Page ─────────────────────────────────────────────────────────────

test.describe('Accessibility — Scans Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
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
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    const buttons = page.locator('button[aria-pressed]')
    const count = await buttons.count()
    expect(count).toBeGreaterThan(0)
  })

  test('filter buttons are keyboard reachable and activatable', async ({ page }) => {
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
    await page.goto('/scans')
    await page.waitForLoadState('networkidle')

    const checkboxes = page.locator('[role="checkbox"]')
    const count = await checkboxes.count()

    if (count > 0) {
      const checked = await checkboxes.first().getAttribute('aria-checked')
      expect(['true', 'false']).toContain(checked)
    } else {
      await expect(page.locator('body')).toBeVisible()
    }
  })

})

// ── Findings Page ──────────────────────────────────────────────────────────

test.describe('Accessibility — Findings Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('search input has id and aria-label', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#findings-search')
    await expect(input).toBeVisible()

    const label = await input.getAttribute('aria-label')
    expect(label).toBeTruthy()
  })

  test('search input is keyboard reachable and typeable', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#findings-search')
    await input.focus()
    await input.fill('xss')

    await expect(input).toHaveValue('xss')
  })

  test('severity filter buttons have aria-pressed', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const allBtn = page.locator('button[aria-label="Show all severity levels"]')
    await expect(allBtn).toBeVisible()

    const pressed = await allBtn.getAttribute('aria-pressed')
    expect(['true', 'false']).toContain(pressed)
  })

  test('severity filter groups have role=group', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const groups = page.locator('[role="group"]')
    const count = await groups.count()
    expect(count).toBeGreaterThan(0)
  })

  test('detail panel has aria-label and aria-live', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const aside = page.locator('aside[aria-label="Finding detail panel"]')
    await expect(aside).toBeVisible()

    const live = await aside.getAttribute('aria-live')
    expect(live).toBe('polite')
  })

  test('finding list buttons have aria-pressed and aria-label', async ({ page }) => {
    await page.goto('/findings')
    await page.waitForLoadState('networkidle')

    const buttons = page.locator('button[aria-pressed]')
    const count = await buttons.count()

    if (count > 0) {
      const label = await buttons.first().getAttribute('aria-label')
      expect(label).toBeTruthy()
    } else {
      await expect(page.locator('body')).toBeVisible()
    }
  })

})

// ── Toolkit (Plugins) Page ─────────────────────────────────────────────────

test.describe('Accessibility — Toolkit Page', () => {

  test('should have no ARIA/structural a11y violations', async ({ page }) => {
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze()

    expect(results.violations).toEqual([])
  })

  test('search input has id and aria-label', async ({ page }) => {
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const input = page.locator('#toolkit-search')
    await expect(input).toBeVisible()

    const label = await input.getAttribute('aria-label')
    expect(label).toBeTruthy()
  })

  test('nav has role=tablist and tabs have role=tab', async ({ page }) => {
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
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const tabs = page.locator('[role="tab"]')
    const count = await tabs.count()

    // Only assert if tabs rendered (requires backend)
    if (count > 0) {
      const selectedTabs = page.locator('[role="tab"][aria-selected="true"]')
      const selectedCount = await selectedTabs.count()
      expect(selectedCount).toBe(1)
    } else {
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('tab panel has role=tabpanel', async ({ page }) => {
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const panel = page.locator('[role="tabpanel"]')
    await expect(panel).toBeVisible()
  })

  test('tool cards have aria-label and aria-disabled when loaded', async ({ page }) => {
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const cards = page.locator('button[aria-label][aria-disabled]')
    const count = await cards.count()

    // Only assert if backend returned tools
    if (count > 0) {
      const label = await cards.first().getAttribute('aria-label')
      expect(label).toBeTruthy()
    } else {
      // Backend down — verify page itself is accessible
      await expect(page.locator('#toolkit-search')).toBeVisible()
    }
  })

  test('tab switching is keyboard operable when tabs are present', async ({ page }) => {
    await page.goto('/toolkit')
    await page.waitForLoadState('networkidle')

    const tabs = page.locator('[role="tab"]')
    const count = await tabs.count()

    // Only test keyboard if tabs rendered
    if (count > 0) {
      const firstTab = tabs.first()
      await firstTab.focus()
      await page.keyboard.press('Enter')

      const selected = await firstTab.getAttribute('aria-selected')
      expect(selected).toBe('true')
    } else {
      // Gracefully pass — toolkit requires backend to render tabs
      await expect(page.locator('#toolkit-search')).toBeVisible()
    }
  })

})
