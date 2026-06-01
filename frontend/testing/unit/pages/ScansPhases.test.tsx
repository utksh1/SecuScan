import { render, act, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import Scans from '../../../src/pages/Scans';

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

function makeTask(id: string, status: string, scan_phase?: string) {
  return {
    task_id: id,
    plugin_id: 'nmap',
    tool: 'Nmap',
    target: '127.0.0.1',
    status,
    scan_phase: scan_phase || null,
    created_at: '2026-01-01T00:00:00',
    started_at: status === 'running' ? '2026-01-01T00:00:01' : null,
    completed_at: null,
    duration_seconds: null,
    preset: null,
    inputs: { target: '127.0.0.1' },
  };
}

const RUNNING_WITH_PHASE_RESPONSE = {
  tasks: [makeTask('task-1', 'running', 'running_command')],
  pagination: { total_items: 1 },
};

const QUEUED_RESPONSE = {
  tasks: [makeTask('task-2', 'queued')],
  pagination: { total_items: 1 },
};

let fetchSpy: ReturnType<typeof vi.fn>;

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

async function tickTime(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function renderScans() {
  return render(
    <MemoryRouter>
      <Scans />
    </MemoryRouter>,
  );
}

describe('Scans — phase display', () => {
  beforeEach(() => {
    vi.useFakeTimers();

    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(RUNNING_WITH_PHASE_RESPONSE),
    });
    vi.stubGlobal('fetch', fetchSpy);

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  function clickExpand() {
    const card = screen.getByText('Nmap').closest('[class*="cursor-pointer"]') as HTMLElement;
    act(() => { card.click(); });
  }

  it('shows phase for a running task in expanded details', async () => {
    renderScans();
    await flush();

    clickExpand();
    await flush();

    expect(screen.getByText(/RUNNING COMMAND/i)).toBeTruthy();
  });

  it('does not show phase for queued task', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(QUEUED_RESPONSE),
    });

    renderScans();
    await flush();
    await tickTime(5000);

    clickExpand();
    await flush();

    expect(screen.queryByText(/PHASE/i)).toBeNull();
  });

  it('updates phase when polling returns a running task with phase', async () => {
    renderScans();
    await flush();

    fetchSpy.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          tasks: [makeTask('task-1', 'running', 'parsing')],
          pagination: { total_items: 1 },
        }),
    });

    await tickTime(5000);

    clickExpand();
    await flush();

    expect(screen.getByText(/PARSING/i)).toBeTruthy();
  });
});
