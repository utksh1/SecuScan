/**
 * Tests for ScanScheduleForm component
 *
 * Uses React Testing Library for modern, user-centric testing
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScanScheduleForm from './ScanScheduleForm';
import '@testing-library/jest-dom';

describe('ScanScheduleForm Component', () => {
  let mockOnSubmit;
  let mockOnCancel;

  beforeEach(() => {
    mockOnSubmit = jest.fn().mockResolvedValue(undefined);
    mockOnCancel = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders form with all required fields', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      expect(screen.getByText('Configure Recurring Scan')).toBeInTheDocument();
      expect(screen.getByLabelText(/Cron Expression/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Timezone/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Blackout Window/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save Schedule/i })).toBeInTheDocument();
    });

    test('renders with default values', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      expect(screen.getByDisplayValue('0 2 * * *')).toBeInTheDocument();
      expect(screen.getByDisplayValue('UTC')).toBeInTheDocument();
    });

    test('renders cancel button when onCancel prop is provided', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    });

    test('renders helpful documentation text', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      expect(screen.getByText(/5-part cron syntax/i)).toBeInTheDocument();
      expect(screen.getByText(/IANA timezone/i)).toBeInTheDocument();
      expect(screen.getByText(/24-hour/i)).toBeInTheDocument();
    });
  });

  describe('Cron Expression Validation', () => {
    test('accepts valid cron expressions', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 */6 * * *');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            cron_expression: '0 */6 * * *',
          })
        );
      });
    });

    test('rejects cron with insufficient parts', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 2 *');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/exactly 5 fields/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    test('rejects cron with too many parts', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 2 * * * *');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/exactly 5 fields/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    test('rejects empty cron expression', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/required/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Blackout Window Validation', () => {
    test('allows blackout window with both start and end times', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const startTimeInput = screen.getAllByRole('textbox').find(
        el => el.getAttribute('type') === 'time' && el.id === 'blackout-start'
      ) || screen.getByDisplayValue('');

      // Since time inputs are HTML5, we need to set them properly
      const timeInputs = screen.getAllByRole('textbox').filter(el => el.type === 'time');

      if (timeInputs.length >= 2) {
        await user.type(timeInputs[0], '22:00');
        await user.type(timeInputs[1], '06:00');
      }

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled();
      });
    });

    test('rejects blackout with only start time', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const timeInputs = screen.getAllByRole('textbox').filter(el => el.type === 'time');

      if (timeInputs.length >= 1) {
        // Set only start time
        fireEvent.change(timeInputs[0], { target: { value: '22:00' } });
      }

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/Both start and end times must be provided/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    test('rejects blackout with only end time', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const timeInputs = screen.getAllByRole('textbox').filter(el => el.type === 'time');

      if (timeInputs.length >= 2) {
        // Set only end time
        fireEvent.change(timeInputs[1], { target: { value: '06:00' } });
      }

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/Both start and end times must be provided/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    test('allows empty blackout window', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      // Don't set any blackout times, just submit
      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            blackout_start: null,
            blackout_end: null,
          })
        );
      });
    });
  });

  describe('Timezone Selection', () => {
    test('allows changing timezone', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const tzSelect = screen.getByDisplayValue('UTC');
      await user.selectOptions(tzSelect, 'America/New_York');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            timezone: 'America/New_York',
          })
        );
      });
    });

    test('includes common timezones in the dropdown', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const tzSelect = screen.getByDisplayValue('UTC');
      expect(tzSelect).toHaveDisplayValue('UTC');

      // Verify some common timezones are available
      const options = Array.from(tzSelect.querySelectorAll('option')).map(opt => opt.value);
      expect(options).toContain('America/New_York');
      expect(options).toContain('Asia/Kolkata');
      expect(options).toContain('Europe/London');
    });
  });

  describe('Form Submission', () => {
    test('calls onSubmit with correct payload', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      const tzSelect = screen.getByDisplayValue('UTC');

      await user.clear(cronInput);
      await user.type(cronInput, '0 12 * * *');
      await user.selectOptions(tzSelect, 'Asia/Kolkata');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          cron_expression: '0 12 * * *',
          timezone: 'Asia/Kolkata',
          blackout_start: null,
          blackout_end: null,
        });
      });
    });

    test('disables submit button while submitting', async () => {
      const user = userEvent.setup();
      mockOnSubmit.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const submitButton = screen.getByRole('button', { name: /Save Schedule/i });

      await user.click(submitButton);

      expect(submitButton).toBeDisabled();
    });

    test('displays success message after successful submission', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(screen.getByText(/Schedule saved successfully/i)).toBeInTheDocument();
      });
    });

    test('resets form after successful submission', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 12 * * *');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(cronInput).toHaveDisplayValue('0 2 * * *');
      });
    });
  });

  describe('Error Handling', () => {
    test('displays error message on submission failure', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Server error occurred';
      mockOnSubmit.mockRejectedValue(new Error(errorMessage));

      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    test('clears previous errors when user changes input', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      // Trigger validation error
      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 2');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      expect(screen.getByText(/exactly 5 fields/i)).toBeInTheDocument();

      // Fix the cron and verify error clears
      await user.clear(cronInput);
      await user.type(cronInput, '0 2 * * *');

      // Error should clear when form is resubmitted successfully
      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        expect(screen.queryByText(/exactly 5 fields/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Cancel Functionality', () => {
    test('calls onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

      await user.click(screen.getByRole('button', { name: /Cancel/i }));

      expect(mockOnCancel).toHaveBeenCalled();
    });

    test('disables cancel button while submitting', async () => {
      const user = userEvent.setup();
      mockOnSubmit.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<ScanScheduleForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />);

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      const submitButton = screen.getByRole('button', { name: /Save Schedule/i });

      await user.click(submitButton);

      expect(cancelButton).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    test('form has proper ARIA labels and descriptions', () => {
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      expect(screen.getByLabelText(/Cron Expression/i)).toHaveAttribute('aria-describedby');
      expect(screen.getByLabelText(/Timezone/i)).toHaveAttribute('aria-describedby');
    });

    test('error alerts have proper ARIA role', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      const cronInput = screen.getByDisplayValue('0 2 * * *');
      await user.clear(cronInput);
      await user.type(cronInput, '0 2');

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      const errorAlert = screen.getByRole('alert');
      expect(errorAlert).toBeInTheDocument();
    });

    test('success messages have proper ARIA role', async () => {
      const user = userEvent.setup();
      render(<ScanScheduleForm onSubmit={mockOnSubmit} />);

      await user.click(screen.getByRole('button', { name: /Save Schedule/i }));

      await waitFor(() => {
        const successStatus = screen.getByRole('status');
        expect(successStatus).toBeInTheDocument();
      });
    });
  });
});
