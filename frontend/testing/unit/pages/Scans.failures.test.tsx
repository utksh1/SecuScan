import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import Scans from '../../../src/pages/Scans';
import { ToastProvider } from '../../../src/components/ToastContext';

vi.mock('../../../src/api', () => ({
  API_BASE: 'http://localhost',
  deleteTask: vi.fn(),
  clearAllTasks: vi.fn(),
  bulkDeleteTasks: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => vi.fn() };
});

const COMPLETED_TASK = {
  task_id: 'task-abc-123',
  plugin_id: 'nmap',
  tool: 'Nmap Scanner',
  target: 'example.com',
  status: 'completed' as const,
  created_at: '2026-05-29T10:00:00Z',
};

const ONE_TASK_RESPONSE = {
  tasks: [COMPLETED_TASK],
  pagination: { total_items: 1 },
};

const TWO_TASK_RESPONSE = {
  tasks: [
    COMPLETED_TASK,
    { ...COMPLETED_TASK, task_id: 'task-def-456', tool: 'Second Scanner' },
  ],
  pagination: { total_items: 2 },
};

function renderScans() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <Scans />
      </ToastProvider>
    </MemoryRouter>,
  );
}

async function waitForTasks(toolName: string) {
  await screen.findByText(toolName, {}, { timeout: 3000 });
}

async function expandTask(toolName: string) {
  const card = await screen.findByText(toolName);
  fireEvent.click(card);
  await screen.findByRole('button', { name: /delete_record/i });
}

async function clickConfirm() {
  const confirmBtn = await screen.findByRole('button', { name: /^confirm$/i });
  fireEvent.click(confirmBtn);
}

beforeEach(() => {
  vi.useRealTimers();
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => 'visible',
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Scans — destructive-action failure feedback', () => {
  describe('handleTaskDelete failure', () => {
    beforeEach(() => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(ONE_TASK_RESPONSE),
      }));
    });

    it('shows an error toast when deleteTask rejects', async () => {
      const { deleteTask } = await import('../../../src/api');
      vi.mocked(deleteTask).mockRejectedValueOnce(new Error('backend crash'));

      renderScans();
      await waitForTasks('Nmap Scanner');
      await expandTask('Nmap Scanner');

      fireEvent.click(screen.getByRole('button', { name: /delete_record/i }));
      await clickConfirm();

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/failed to delete task/i)).toBeInTheDocument();
    });

    it('does not remove the task from the list when deleteTask rejects', async () => {
      const { deleteTask } = await import('../../../src/api');
      vi.mocked(deleteTask).mockRejectedValueOnce(new Error('network error'));

      renderScans();
      await waitForTasks('Nmap Scanner');
      await expandTask('Nmap Scanner');

      fireEvent.click(screen.getByRole('button', { name: /delete_record/i }));
      await clickConfirm();

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText('Nmap Scanner')).toBeInTheDocument();
    });
  });

  describe('handleBulkDelete failure', () => {
    beforeEach(() => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(TWO_TASK_RESPONSE),
      }));
    });

    it('shows an error toast when bulkDeleteTasks rejects', async () => {
      const { bulkDeleteTasks } = await import('../../../src/api');
      vi.mocked(bulkDeleteTasks).mockRejectedValueOnce(new Error('bulk delete failed'));

      renderScans();
      await waitForTasks('Nmap Scanner');

      fireEvent.click(screen.getByRole('button', { name: /select_all/i }));

      const bulkBtn = await screen.findByRole('button', { name: /prune_selected_records/i });
      fireEvent.click(bulkBtn);
      await clickConfirm();

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/failed to delete some tasks/i)).toBeInTheDocument();
    });

    it('keeps tasks in the list when bulkDeleteTasks rejects', async () => {
      const { bulkDeleteTasks } = await import('../../../src/api');
      vi.mocked(bulkDeleteTasks).mockRejectedValueOnce(new Error('bulk delete failed'));

      renderScans();
      await waitForTasks('Nmap Scanner');

      fireEvent.click(screen.getByRole('button', { name: /select_all/i }));

      const bulkBtn = await screen.findByRole('button', { name: /prune_selected_records/i });
      fireEvent.click(bulkBtn);
      await clickConfirm();

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText('Nmap Scanner')).toBeInTheDocument();
      expect(screen.getByText('Second Scanner')).toBeInTheDocument();
    });
  });

  describe('handleClearAll failure', () => {
    beforeEach(() => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(ONE_TASK_RESPONSE),
      }));
    });

    it('shows an error toast when clearAllTasks rejects', async () => {
      const { clearAllTasks } = await import('../../../src/api');
      vi.mocked(clearAllTasks).mockRejectedValueOnce(new Error('tasks still running'));

      renderScans();
      await waitForTasks('Nmap Scanner');

      fireEvent.click(screen.getByRole('button', { name: /purge_all_records/i }));
      await clickConfirm();

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument();
      });
      expect(screen.getByText(/failed to clear history/i)).toBeInTheDocument();
    });
  });
});