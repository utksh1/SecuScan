import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import Scans from '../../../src/pages/Scans';
import { useFetchScans } from '../../../src/hooks/useFetchScans';

// 1. Mock the custom hook that pulls data into the Scans dashboard
vi.mock('../../../src/hooks/useFetchScans', () => ({
  useFetchScans: vi.fn(),
}));

const mockScansData = [
  { id: 'scan-1', name: 'Scan Iteration A', status: 'completed', findings: [] },
  { id: 'scan-2', name: 'Scan Iteration B', status: 'completed', findings: [] },
  { id: 'scan-3', name: 'Scan Iteration C', status: 'failed', findings: [] },
];

describe('Scans Comparison Dashboard - Integration Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Requirement A: Selecting two completed scans
  test('allows selection of two completed scans and renders comparison component', async () => {
    vi.mocked(useFetchScans).mockReturnValue({ scans: mockScansData, loading: false, error: null });
    render(<Scans />);

    const checkA = screen.getByLabelText('Select Scan Iteration A');
    const checkB = screen.getByLabelText('Select Scan Iteration B');

    fireEvent.click(checkA);
    fireEvent.click(checkB);

    const compareBtn = screen.getByRole('button', { name: /Compare Scans/i });
    expect(compareBtn).not.toBeDisabled();
    fireEvent.click(compareBtn);

    expect(screen.getByTestId('report-diff-view')).toBeInTheDocument();
  });

  // Requirement B: Handling Empty Diffs gracefully
  test('displays fallback empty state message when identical scans are compared', async () => {
    vi.mocked(useFetchScans).mockReturnValue({ 
      scans: [mockScansData[0], mockScansData[0]], 
      loading: false, 
      error: null 
    });
    render(<Scans />);

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole('button', { name: /Compare Scans/i }));

    expect(screen.getByText(/No changes detected between these scan iterations/i)).toBeInTheDocument();
  });

  // Requirement C: Handling Failed Fetches smoothly
  test('safely displays error boundary when API request fails', async () => {
    vi.mocked(useFetchScans).mockReturnValue({ scans: [], loading: false, error: 'Failed to fetch scan details' });
    render(<Scans />);

    expect(screen.getByText(/Failed to fetch scan details/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Compare Scans/i })).not.toBeInTheDocument();
  });
});