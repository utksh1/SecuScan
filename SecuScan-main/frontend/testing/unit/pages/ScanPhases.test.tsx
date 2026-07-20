import { render, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TaskDetails from '../../../src/pages/TaskDetails';
import * as api from '../../../src/api';

vi.mock('../../../src/api', () => ({
  API_BASE: 'http://localhost',
  getTaskStatus: vi.fn(),
  getTaskResult: vi.fn(),
  getPluginSchema: vi.fn().mockResolvedValue(null),
  startTask: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useParams: () => ({ taskId: 'test-task-123' }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../../../src/components/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

const RUNNING_TASK = {
  task_id: 'test-task-123',
  plugin_id: 'nmap',
  tool: 'Nmap',
  target: '127.0.0.1',
  status: 'running',
  scan_phase: 'running_command',
  created_at: '2026-01-01T00:00:00',
  started_at: '2026-01-01T00:00:01',
};

const RESULT_EMPTY = {
  task_id: 'test-task-123',
  plugin_id: 'nmap',
  tool: 'Nmap',
  target: '127.0.0.1',
  timestamp: '2026-01-01T00:00:00',
  status: 'running',
  summary: [],
  findings: [],
  structured: {},
};

function renderTaskDetails() {
  return render(
    <MemoryRouter>
      <TaskDetails />
    </MemoryRouter>,
  );
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('TaskDetails — scan phase display', () => {
  let currentEventSource: any;

  beforeEach(() => {
    vi.useFakeTimers();

    currentEventSource = undefined;
    // Mock EventSource before rendering
    class MockEventSource {
      url: string;
      _onerror: any;
      listeners: Record<string, Function[]> = {};
      constructor(url: string) { this.url = url; currentEventSource = this; }
      addEventListener(event: string, handler: Function) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(handler);
      }
      set onerror(handler: any) { this._onerror = handler; }
      close() {}
    }
    vi.stubGlobal('EventSource', MockEventSource);

    vi.mocked(api.getTaskStatus).mockResolvedValue(RUNNING_TASK);
    vi.mocked(api.getTaskResult).mockResolvedValue(RESULT_EMPTY);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('shows loading screen with phase label while task is loading', async () => {
    vi.mocked(api.getTaskStatus).mockImplementation(() => new Promise(() => {}));

    renderTaskDetails();
    await flush();

    expect(document.body.textContent).toContain('DECRYPTING_BRIEFING');
  });

  it('shows phase progress for running_command phase', async () => {
    renderTaskDetails();
    await flush();
    await flush();

    expect(document.body.textContent).toContain('Executing security scan');
  });

  it('shows phase progress when phase changes via SSE', async () => {
    renderTaskDetails();
    await flush();
    await flush();

    expect(currentEventSource).toBeTruthy();
    expect(currentEventSource.listeners['phase']).toBeTruthy();
    act(() => {
      currentEventSource.listeners['phase'].forEach((fn: Function) =>
        fn({ data: JSON.stringify({ scan_phase: 'parsing' }) }),
      );
    });

    await flush();
    expect(document.body.textContent).toContain('Parsing scan results');
  });

  it('shows reporting phase label', async () => {
    renderTaskDetails();
    await flush();
    await flush();

    expect(currentEventSource).toBeTruthy();
    expect(currentEventSource.listeners['phase']).toBeTruthy();
    act(() => {
      currentEventSource.listeners['phase'].forEach((fn: Function) =>
        fn({ data: JSON.stringify({ scan_phase: 'reporting' }) }),
      );
    });

    await flush();
    expect(document.body.textContent).toContain('Generating reports');
  });
});
