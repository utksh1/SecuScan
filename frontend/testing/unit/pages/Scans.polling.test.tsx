import { render, act, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import Scans from '../../../src/pages/Scans';
import { ToastProvider } from '../../../src/components/ToastContext'

// ── Mocks ────────────────────────────────────────────────────────────────────

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

const EMPTY_RESPONSE = { tasks: [], pagination: { total_items: 0 } };
const LATEST_RESPONSE = {
  tasks: [{
    task_id: 'latest-task',
    plugin_id: 'nmap',
    tool: 'Latest Tool',
    target: 'latest.example.com',
    status: 'completed',
    created_at: '2026-05-29T10:00:00Z',
  }],
  pagination: { total_items: 1 },
};
const STALE_RESPONSE = {
  tasks: [{
    task_id: 'stale-task',
    plugin_id: 'nmap',
    tool: 'Stale Tool',
    target: 'stale.example.com',
    status: 'completed',
    created_at: '2026-05-29T09:00:00Z',
  }],
  pagination: { total_items: 1 },
};

let fetchSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchSpy = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(EMPTY_RESPONSE),
  });
  vi.stubGlobal('fetch', fetchSpy);

  // Use fake timers; microtasks drained via Promise.resolve() chains in flush()/tickTime()
  vi.useFakeTimers();

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

function renderScans() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <Scans />
      </ToastProvider>
    </MemoryRouter>
  );
}

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => state,
  });
  document.dispatchEvent(new Event('visibilitychange'));
}

// Drain pending microtasks — works with Vitest 2.1.x.
async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

// Advance fake timers then drain microtasks so fetch callbacks settle.
async function tickTime(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function deferredResponse(body: unknown) {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((res) => {
    resolve = res;
  });
  return {
    promise,
    resolve: () => resolve({
      ok: true,
      json: () => Promise.resolve(body),
    } as Response),
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('Scans — visibility-aware polling', () => {
  it('fires one fetch on mount', async () => {
    renderScans();
    await flush();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('polls every 5 s while the tab is visible', async () => {
    renderScans();
    await flush();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await tickTime(5_000);
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    await tickTime(5_000);
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it('updates scan status badges automatically during polling', async () => {
    const runningResponse = {
      tasks: [{
        task_id: 'task-123',
        plugin_id: 'nmap',
        tool: 'Automatic Status Scan',
        target: 'auto.example.com',
        status: 'running',
        created_at: '2026-05-29T10:00:00Z',
        started_at: '2026-05-29T10:01:00Z',
      }],
      pagination: { total_items: 1 },
    };

    const completedResponse = {
      tasks: [{
        task_id: 'task-123',
        plugin_id: 'nmap',
        tool: 'Automatic Status Scan',
        target: 'auto.example.com',
        status: 'completed',
        created_at: '2026-05-29T10:00:00Z',
        started_at: '2026-05-29T10:01:00Z',
        completed_at: '2026-05-29T10:05:00Z',
      }],
      pagination: { total_items: 1 },
    };

    fetchSpy.mockReset();
    fetchSpy
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(runningResponse) } as Response)
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(completedResponse) } as Response);

    renderScans();
    await flush();

    expect(screen.getByText('running')).toBeInTheDocument();

    await tickTime(5_000);
    await flush();

    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.queryByText('running')).not.toBeInTheDocument();
  });

  it('stops polling entirely when the tab is hidden', async () => {
    renderScans();
    await flush();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    setVisibility('hidden');
    await flush();

    await tickTime(15_000);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('resumes polling immediately when the tab becomes visible again', async () => {
    renderScans();
    await flush();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    setVisibility('hidden');
    await tickTime(15_000);
    expect(fetchSpy).toHaveBeenCalledTimes(1); // still paused

    setVisibility('visible');
    await flush(); // immediate fetch on resume
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    await tickTime(5_000); // interval restarts
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it('does not double-poll if tab was never hidden', async () => {
    renderScans();
    await flush();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await tickTime(5_000);
    await tickTime(5_000);
    await tickTime(5_000);
    // 1 mount + 3 ticks = exactly 4
    expect(fetchSpy).toHaveBeenCalledTimes(4);
  });

  it('cleans up the interval and listener on unmount', async () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener');

    const { unmount } = renderScans();
    await flush();
    const callsAfterMount = fetchSpy.mock.calls.length;

    unmount();

    await tickTime(15_000);
    // No extra fetches after unmount
    expect(fetchSpy).toHaveBeenCalledTimes(callsAfterMount);
    expect(removeSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
  });

  it('ignores stale task responses when a newer poll finishes first', async () => {
    const stale = deferredResponse(STALE_RESPONSE);
    const latest = deferredResponse(LATEST_RESPONSE);
    fetchSpy.mockReset();
    fetchSpy.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(EMPTY_RESPONSE),
    });
    fetchSpy
      .mockReturnValueOnce(stale.promise)
      .mockReturnValueOnce(latest.promise);

    renderScans();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await tickTime(5_000);
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    await act(async () => {
      latest.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('Latest Tool')).toBeInTheDocument();

    await act(async () => {
      stale.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText('Latest Tool')).toBeInTheDocument();
    expect(screen.queryByText('Stale Tool')).not.toBeInTheDocument();
  });
});
