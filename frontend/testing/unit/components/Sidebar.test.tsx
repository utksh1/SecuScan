import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Sidebar from '../../../src/components/Sidebar';

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

// Mock framer-motion to render plain elements so tests focus on behavior,
// not animation internals.
vi.mock('framer-motion', async () => {
  const ReactModule = await import('react');
  const createMotionProxy = () =>
    new Proxy(
      {},
      {
        get(_target: unknown, prop: string) {
          return ReactModule.forwardRef((props: Record<string, unknown>, ref: React.Ref<unknown>) => {
            // Strip framer-specific props so they don't leak to the DOM
            const {
              initial: _initial,
              animate: _animate,
              exit: _exit,
              transition: _transition,
              layoutId: _layoutId,
              whileHover: _whileHover,
              whileTap: _whileTap,
              ...rest
            } = props;
            return ReactModule.createElement(prop, { ...rest, ref });
          });
        },
      },
    );

  return {
    motion: createMotionProxy(),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Minimal ThemeToggle stub — the Sidebar imports it but its internals
// are not under test here.
vi.mock('../../../src/components/ThemeToggle', () => ({
  default: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/**
 * Renders the Sidebar inside a MemoryRouter so NavLink can resolve
 * active state based on `initialRoute`.
 */
function renderSidebar(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Sidebar />
    </MemoryRouter>,
  );
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  /* ---------------------------------------------------------------
   *  Collapse Persistence
   * --------------------------------------------------------------- */
  describe('collapse persistence', () => {
    it('defaults to expanded when localStorage has no saved value', () => {
      renderSidebar();

      // All nav labels should be visible when expanded
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Toolkit')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('restores collapsed state from localStorage', () => {
      localStorage.setItem('sidebar-expanded', 'false');
      renderSidebar();

      // When collapsed the aside should have the narrow width style
      const aside = document.querySelector('aside');
      expect(aside).toBeInTheDocument();

      // Labels should still render (AnimatePresence mock renders children),
      // but the component reads the persisted value; verify localStorage was
      // consumed correctly by checking that the toggle icon shows the
      // "expand" arrow.
      expect(
        screen.getByText('keyboard_double_arrow_right'),
      ).toBeInTheDocument();
    });

    it('restores expanded state from localStorage', () => {
      localStorage.setItem('sidebar-expanded', 'true');
      renderSidebar();

      // Expanded state shows the "collapse" arrow
      expect(
        screen.getByText('keyboard_double_arrow_left'),
      ).toBeInTheDocument();
    });

    it('persists collapsed state to localStorage after toggling', async () => {
      const user = userEvent.setup();
      renderSidebar();

      // Initially expanded (default)
      expect(localStorage.getItem('sidebar-expanded')).toBe('true');

      // Click the sidebar to toggle collapse
      await user.click(screen.getByRole('complementary'));

      expect(localStorage.getItem('sidebar-expanded')).toBe('false');
    });

    it('persists expanded state when toggling back open', async () => {
      const user = userEvent.setup();
      localStorage.setItem('sidebar-expanded', 'false');
      renderSidebar();

      await user.click(screen.getByRole('complementary'));

      expect(localStorage.getItem('sidebar-expanded')).toBe('true');
    });

    it('toggles via the dedicated toggle button', async () => {
      const user = userEvent.setup();
      renderSidebar();

      await user.click(
        screen.getByRole('button', { name: 'keyboard_double_arrow_left' }),
      );

      // After clicking the toggle button, the sidebar should be collapsed
      expect(localStorage.getItem('sidebar-expanded')).toBe('false');
      expect(
        screen.getByText('keyboard_double_arrow_right'),
      ).toBeInTheDocument();
    });
  });

  /* ---------------------------------------------------------------
   *  Active Nav State
   * --------------------------------------------------------------- */
  describe('active nav rendering', () => {
    it('marks Dashboard link as active on "/"', () => {
      renderSidebar('/');

      const dashboardLink = screen.getByText('Dashboard').closest('a')!;
      expect(dashboardLink).toHaveAttribute('href', '/');
      expect(dashboardLink).toHaveAttribute('aria-current', 'page');
    });

    it('marks Toolkit link as active on "/toolkit"', () => {
      renderSidebar('/toolkit');

      const toolkitLink = screen.getByText('Toolkit').closest('a')!;
      expect(toolkitLink).toHaveAttribute('href', '/toolkit');
      expect(toolkitLink).toHaveAttribute('aria-current', 'page');
    });

    it('marks Settings link as active on "/settings"', () => {
      renderSidebar('/settings');

      const settingsLink = screen.getByText('Settings').closest('a')!;
      expect(settingsLink).toHaveAttribute('href', '/settings');
      expect(settingsLink).toHaveAttribute('aria-current', 'page');
    });

    it('marks Registry link as active on "/scans"', () => {
      renderSidebar('/scans');

      const scansLink = screen.getByText('Registry').closest('a')!;
      expect(scansLink).toHaveAttribute('href', '/scans');
      expect(scansLink).toHaveAttribute('aria-current', 'page');
    });

    it('does not mark non-active links with active styling', () => {
      renderSidebar('/settings');

      const dashboardLink = screen.getByText('Dashboard').closest('a')!;
      expect(dashboardLink).not.toHaveAttribute('aria-current');
    });

    it('renders active indicator elements for the active link', () => {
      renderSidebar('/');

      const dashboardLink = screen.getByText('Dashboard').closest('a')!;
      // The active link contains the glow div (layoutId="activeGlow") and
      // the side bar div (layoutId="activeBar")
      const glowDiv = dashboardLink.querySelector('[class*="bg-rag-red/5"]');
      expect(glowDiv).toBeInTheDocument();
    });

    it('does not render active indicator elements for inactive links', () => {
      renderSidebar('/settings');

      const dashboardLink = screen.getByText('Dashboard').closest('a')!;
      // Inactive link should NOT contain the active glow element
      const glowDivs = dashboardLink.querySelectorAll('[class*="bg-rag-red/5"]');
      expect(glowDivs.length).toBe(0);
    });
  });

  /* ---------------------------------------------------------------
   *  Highlighted Nav State
   * --------------------------------------------------------------- */
  describe('highlighted nav rendering', () => {
    it('applies highlight styling to the Toolkit link when not active', () => {
      // Navigate to a route that is NOT /toolkit so Toolkit is highlighted
      // but not active
      renderSidebar('/');

      const toolkitLink = screen.getByText('Toolkit').closest('a')!;
      expect(toolkitLink.className).toContain('bg-rag-blue/15');
      expect(toolkitLink.className).toContain('border-rag-blue/30');
    });

    it('applies highlight icon styling to the Toolkit icon when not active', () => {
      renderSidebar('/');

      // The Toolkit icon should show the highlighted (blue) text
      const toolkitIcon = screen.getByText('add_circle');
      expect(toolkitIcon.className).toContain('text-rag-blue');
    });

    it('does not apply highlight styling to non-highlight links', () => {
      renderSidebar('/');

      // Dashboard is active here so skip it; check Findings which is
      // neither active nor highlighted
      const findingsLink = screen.getByText('Findings').closest('a')!;
      expect(findingsLink.className).not.toContain('bg-rag-blue/15');
    });

    it('applies active styling instead of highlight when Toolkit is the active route', () => {
      renderSidebar('/toolkit');

      const toolkitLink = screen.getByText('Toolkit').closest('a')!;
      expect(toolkitLink).toHaveAttribute('aria-current', 'page');
      // Highlight-specific classes should NOT be present
      expect(toolkitLink.className).not.toContain('bg-rag-blue/15');
    });
  });

  /* ---------------------------------------------------------------
   *  Nav Structure
   * --------------------------------------------------------------- */
  describe('navigation structure', () => {
    it('renders all expected navigation links', () => {
      renderSidebar();

      const expectedLabels = [
        'Toolkit',
        'Dashboard',
        'Registry',
        'Findings',
        'Reports',
        'Workflows',
        'Settings',
      ];

      for (const label of expectedLabels) {
        expect(screen.getByText(label)).toBeInTheDocument();
      }
    });

    it('renders section headers when expanded', () => {
      renderSidebar();

      expect(screen.getByText('Monitor')).toBeInTheDocument();
      expect(screen.getByText('Analyze')).toBeInTheDocument();
    });
  });
});
