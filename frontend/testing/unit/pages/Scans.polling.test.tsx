import { render, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import Scans from '../../../src/pages/Scans';

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

let fetchSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchSpy = vi.fn().mockResolvedValue({
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
      <Scans />
    </MemoryRouter>,
  );
}

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => state,
  });
  document.dispatchEvent(new Event('visibilitychange'));
}

// Advance timers by ms then drain all pending microtasks (promise callbacks)
async function tickTime(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    
  });
}

// Just drain microtasks without advancing time
async function flush() {
  await act(async () => {
    
  });
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
});
