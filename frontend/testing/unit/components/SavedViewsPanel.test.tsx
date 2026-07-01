import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SavedViewsPanel from '../../../src/components/SavedViewsPanel'

/* ------------------------------------------------------------------ */
/*  Mocks                                                             */
/* ------------------------------------------------------------------ */

// Mock framer-motion to render plain elements so tests focus on behavior,
// not animation internals.
vi.mock('framer-motion', async () => {
  const ReactModule = await import('react')
  const createMotionProxy = () =>
    new Proxy(
      {},
      {
        get(_target: unknown, prop: string) {
          return ReactModule.forwardRef((props: Record<string, unknown>, ref: React.Ref<unknown>) => {
            const {
              initial: _initial,
              animate: _animate,
              exit: _exit,
              transition: _transition,
              layoutId: _layoutId,
              whileHover: _whileHover,
              whileTap: _whileTap,
              layout: _layout,
              ...rest
            } = props
            return ReactModule.createElement(prop, { ...rest, ref })
          })
        },
      },
    )

  return {
    motion: createMotionProxy(),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  }
})

/* ------------------------------------------------------------------ */
/*  Test Data & Helpers                                               */
/* ------------------------------------------------------------------ */

const mockPreset = {
  severity: 'high',
  target: 'all',
  scanner: 'all',
  sortMode: 'severity',
  dateFrom: '',
  dateTo: '',
  searchQuery: '',
}

const mockViews = [
  {
    id: 'view-1',
    name: 'Critical Findings Only',
    preset: { ...mockPreset, severity: 'critical' },
    createdAt: '2026-06-30T12:00:00.000Z',
    updatedAt: '2026-06-30T12:00:00.000Z',
  },
  {
    id: 'view-2',
    name: 'High Severity Filters',
    preset: mockPreset,
    createdAt: '2026-06-30T12:00:00.000Z',
    updatedAt: '2026-06-30T12:00:00.000Z',
  },
]

function renderSavedViewsPanel(props = {}) {
  const defaultProps = {
    views: mockViews,
    loading: false,
    saveView: vi.fn().mockImplementation((name, preset) => {
      return Promise.resolve({
        id: 'new-view-id',
        name,
        preset,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
    }),
    deleteView: vi.fn().mockResolvedValue(undefined),
    renameView: vi.fn().mockResolvedValue(undefined),
    currentPreset: mockPreset,
    onApply: vi.fn(),
    ...props,
  }
  return {
    ...render(<SavedViewsPanel {...defaultProps} />),
    props: defaultProps,
  }
}

/* ------------------------------------------------------------------ */
/*  Tests                                                             */
/* ------------------------------------------------------------------ */

describe('SavedViewsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('UI basics and toggle', () => {
    it('is closed by default and does not render the panel dialog', () => {
      renderSavedViewsPanel()
      expect(screen.queryByRole('dialog', { name: 'Saved filter views panel' })).not.toBeInTheDocument()
    })

    it('opens and closes when toggling the main button', async () => {
      const user = userEvent.setup()
      renderSavedViewsPanel()

      const toggleButton = screen.getByRole('button', { name: 'Saved filter views' })
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false')

      // Open
      await user.click(toggleButton)
      expect(toggleButton).toHaveAttribute('aria-expanded', 'true')
      expect(screen.getByRole('dialog', { name: 'Saved filter views panel' })).toBeInTheDocument()

      // Close via header close button
      const closeButton = screen.getByRole('button', { name: 'Close panel' })
      await user.click(closeButton)
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false')
      expect(screen.queryByRole('dialog', { name: 'Saved filter views panel' })).not.toBeInTheDocument()
    })
  })

  describe('Renaming an existing saved view', () => {
    it('enters edit mode on rename button click, showing original name in input', async () => {
      const user = userEvent.setup()
      renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const renameButtons = screen.getAllByRole('button', { name: 'Rename view' })
      await user.click(renameButtons[0])

      const renameInput = screen.getByRole('textbox', { name: 'Rename saved view' })
      expect(renameInput).toBeInTheDocument()
      expect(renameInput).toHaveValue('Critical Findings Only')
      expect(renameInput).toHaveFocus()
    })

    it('submits the new name on Enter key press', async () => {
      const user = userEvent.setup()
      const { props } = renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const renameButtons = screen.getAllByRole('button', { name: 'Rename view' })
      await user.click(renameButtons[0])

      const renameInput = screen.getByRole('textbox', { name: 'Rename saved view' })
      await user.clear(renameInput)
      await user.type(renameInput, 'Super Critical Views{Enter}')

      expect(props.renameView).toHaveBeenCalledWith('view-1', 'Super Critical Views')
      expect(screen.queryByRole('textbox', { name: 'Rename saved view' })).not.toBeInTheDocument()
    })

    it('submits the new name on blur', async () => {
      const user = userEvent.setup()
      const { props } = renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const renameButtons = screen.getAllByRole('button', { name: 'Rename view' })
      await user.click(renameButtons[0])

      const renameInput = screen.getByRole('textbox', { name: 'Rename saved view' })
      await user.clear(renameInput)
      await user.type(renameInput, 'Blurred View Name')

      // Blur by clicking outside on the header text
      await user.click(screen.getByText('Filter_Presets'))

      expect(props.renameView).toHaveBeenCalledWith('view-1', 'Blurred View Name')
      expect(screen.queryByRole('textbox', { name: 'Rename saved view' })).not.toBeInTheDocument()
    })

    it('reverts and cancels edit mode on Escape key press', async () => {
      const user = userEvent.setup()
      const { props } = renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const renameButtons = screen.getAllByRole('button', { name: 'Rename view' })
      await user.click(renameButtons[0])

      const renameInput = screen.getByRole('textbox', { name: 'Rename saved view' })
      await user.type(renameInput, 'Unsaved Changes')
      await user.keyboard('{Escape}')

      expect(props.renameView).not.toHaveBeenCalled()
      expect(screen.queryByRole('textbox', { name: 'Rename saved view' })).not.toBeInTheDocument()
      expect(screen.getByText('Critical Findings Only')).toBeInTheDocument()
    })

    it('reverts and cancels when field is empty or contains only whitespace', async () => {
      const user = userEvent.setup()
      const { props } = renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const renameButtons = screen.getAllByRole('button', { name: 'Rename view' })
      await user.click(renameButtons[0])

      const renameInput = screen.getByRole('textbox', { name: 'Rename saved view' })
      await user.clear(renameInput)
      await user.type(renameInput, '   {Enter}')

      expect(props.renameView).not.toHaveBeenCalled()
      expect(screen.queryByRole('textbox', { name: 'Rename saved view' })).not.toBeInTheDocument()
      expect(screen.getByText('Critical Findings Only')).toBeInTheDocument()
    })
  })

  describe('Deleting a saved view', () => {
    it('demands confirmation and triggers delete on click', async () => {
      const user = userEvent.setup()
      const { props } = renderSavedViewsPanel()

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const deleteButtons = screen.getAllByRole('button', { name: 'Delete view' })
      // Click delete on the second view (High Severity Filters)
      await user.click(deleteButtons[1])

      // Confirm button should be visible now
      const confirmButton = screen.getByRole('button', { name: 'Confirm delete' })
      expect(confirmButton).toBeInTheDocument()
      expect(confirmButton).toHaveTextContent('Confirm')

      // Click confirm delete
      await user.click(confirmButton)

      expect(props.deleteView).toHaveBeenCalledWith('view-2')
      expect(screen.queryByRole('button', { name: 'Confirm delete' })).not.toBeInTheDocument()
    })
  })

  describe('Loading and error states tests', () => {
    it('displays loading indicator and excludes list rows when loading is true', async () => {
      const user = userEvent.setup()
      renderSavedViewsPanel({ loading: true })

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      expect(screen.getByText('Loading presets…')).toBeInTheDocument()
      // View rows should not be rendered
      expect(screen.queryByRole('button', { name: /Apply saved view:/ })).not.toBeInTheDocument()
      expect(screen.queryByText('Critical Findings Only')).not.toBeInTheDocument()
      expect(screen.queryByText('High Severity Filters')).not.toBeInTheDocument()
    })

    it('renders placeholder UI when loading is false and no views are loaded', async () => {
      const user = userEvent.setup()
      renderSavedViewsPanel({ views: [], loading: false })

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      expect(screen.getByText('No Saved Views')).toBeInTheDocument()
      expect(screen.getByText('Configure filters then save above.')).toBeInTheDocument()
      expect(screen.queryByText('Loading presets…')).not.toBeInTheDocument()
    })

    it('displays error and recovers saving state gracefully without altering existing rows on saveView failure', async () => {
      const user = userEvent.setup()
      const saveError = new Error('Save API limit exceeded')
      const saveViewMock = vi.fn().mockRejectedValue(saveError)

      renderSavedViewsPanel({ saveView: saveViewMock })

      await user.click(screen.getByRole('button', { name: 'Saved filter views' }))

      const nameInput = screen.getByRole('textbox', { name: 'Saved view name' })
      await user.type(nameInput, 'Failed Save View')

      const saveButton = screen.getByRole('button', { name: 'Save current filters' })
      await user.click(saveButton)

      // Alert should display the error message
      const alert = await screen.findByRole('alert')
      expect(alert).toHaveTextContent('⚠ Save API limit exceeded')

      // Save button should be interactive/enabled again
      expect(saveButton).not.toBeDisabled()

      // The original rows should remain fully intact and not disappear or be replaced
      expect(screen.getByText('Critical Findings Only')).toBeInTheDocument()
      expect(screen.getByText('High Severity Filters')).toBeInTheDocument()
    })
  })
})
