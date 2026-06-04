import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CopyToClipboard from '../../../src/components/CopyToClipboard';

describe('CopyToClipboard', () => {
  const originalClipboard = navigator.clipboard;
  const writeText = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    writeText.mockReset();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: originalClipboard,
    });
  });

  it('copies text and returns to idle state', async () => {
    writeText.mockResolvedValue(undefined);

    render(<CopyToClipboard textToCopy="raw output" />);

    fireEvent.click(screen.getByRole('button', { name: /copy output/i }));
    await act(async () => {});

    expect(writeText).toHaveBeenCalledWith('raw output');
    expect(screen.getByRole('button', { name: /copied!/i })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.getByRole('button', { name: /copy output/i })).toBeInTheDocument();
  });

  it('shows failure state when clipboard write fails', async () => {
    writeText.mockRejectedValue(new Error('clipboard denied'));
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(<CopyToClipboard textToCopy="raw output" />);

    fireEvent.click(screen.getByRole('button', { name: /copy output/i }));
    await act(async () => {});

    expect(screen.getByRole('button', { name: /copy failed/i })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.getByRole('button', { name: /copy output/i })).toBeInTheDocument();
    consoleError.mockRestore();
  });
});
