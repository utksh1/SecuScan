import React, { useState, ReactNode } from 'react';
import styles from './ScanScheduleForm.module.css';

/**
 * Schedule configuration payload submitted by the form
 */
interface SchedulePayload {
  cron_expression: string;
  timezone: string;
  blackout_start: string | null;
  blackout_end: string | null;
}

/**
 * Component props for ScanScheduleForm
 */
interface ScanScheduleFormProps {
  onSubmit: (payload: SchedulePayload) => Promise<void>;
  onCancel?: () => void;
}

/**
 * Form validation error response
 */
interface ValidationResult {
  valid: boolean;
  message?: string;
}

/**
 * ScanScheduleForm Component
 *
 * A comprehensive form for configuring recurring scheduled scans with:
 * - Cron expression input with 5-part validation
 * - Timezone selection with IANA timezone support
 * - Optional blackout window configuration (time ranges to skip scans)
 * - Client-side validation before submission
 */
const ScanScheduleForm: React.FC<ScanScheduleFormProps> = ({ onSubmit, onCancel }): ReactNode => {
  // Form state
  const [cronExpr, setCronExpr] = useState<string>('0 2 * * *'); // Default: 2 AM daily
  const [timezone, setTimezone] = useState<string>('UTC');
  const [blackoutStart, setBlackoutStart] = useState<string>('');
  const [blackoutEnd, setBlackoutEnd] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Timezone list (common timezones for quick access)
  const commonTimezones: string[] = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Asia/Kolkata',
    'Asia/Bangkok',
    'Asia/Tokyo',
    'Australia/Sydney',
    'Australia/Melbourne'
  ];

  /**
   * Validates cron expression: must contain exactly 5 space-separated parts
   */
  const validateCron = (cron: string): ValidationResult => {
    if (!cron || !cron.trim()) {
      return { valid: false, message: 'Cron expression is required.' };
    }

    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) {
      return {
        valid: false,
        message: `Invalid cron expression. Must contain exactly 5 fields, found ${parts.length}. Format: minute hour day month day-of-week (e.g., "0 2 * * *").`
      };
    }

    // Basic validation: check if each part is non-empty
    if (parts.some(part => !part)) {
      return { valid: false, message: 'Cron expression contains empty fields.' };
    }

    return { valid: true };
  };

  /**
   * Validates time format (HH:MM)
   */
  const validateTimeFormat = (timeStr: string): boolean => {
    if (!timeStr) {
      return true; // Empty is valid
    }

    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    return timeRegex.test(timeStr);
  };

  /**
   * Validates blackout window configuration
   */
  const validateBlackoutWindow = (): ValidationResult => {
    const hasStart = blackoutStart && blackoutStart.trim();
    const hasEnd = blackoutEnd && blackoutEnd.trim();

    // Both or neither should be provided
    if ((hasStart && !hasEnd) || (!hasStart && hasEnd)) {
      return {
        valid: false,
        message: 'Both start and end times must be provided for a blackout window.'
      };
    }

    // Validate time format
    if (hasStart && !validateTimeFormat(blackoutStart)) {
      return {
        valid: false,
        message: 'Blackout start time must be in HH:MM format (e.g., 22:00).'
      };
    }

    if (hasEnd && !validateTimeFormat(blackoutEnd)) {
      return {
        valid: false,
        message: 'Blackout end time must be in HH:MM format (e.g., 06:00).'
      };
    }

    return { valid: true };
  };

  /**
   * Handles form submission with comprehensive validation
   */
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    // Validate cron expression
    const cronValidation = validateCron(cronExpr);
    if (!cronValidation.valid) {
      setError(cronValidation.message || '');
      return;
    }

    // Validate blackout window
    const blackoutValidation = validateBlackoutWindow();
    if (!blackoutValidation.valid) {
      setError(blackoutValidation.message);
      return;
    }

    // Prepare payload
    const payload = {
      cron_expression: cronExpr.trim(),
      timezone: timezone,
      blackout_start: blackoutStart || null,
      blackout_end: blackoutEnd || null
    };

    setIsSubmitting(true);

    try {
      // Call the provided onSubmit callback
      if (typeof onSubmit === 'function') {
        await onSubmit(payload);
        setSuccessMessage('Schedule saved successfully!');

        // Reset form after successful submission
        setCronExpr('0 2 * * *');
        setTimezone('UTC');
        setBlackoutStart('');
        setBlackoutEnd('');
      }
    } catch (err) {
      setError(err.message || 'Failed to save schedule. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className={styles.container} onSubmit={handleSubmit}>
      <div className={styles.header}>
        <h2>Configure Recurring Scan</h2>
        <p className={styles.subtitle}>
          Set up automated periodic scans with timezone support and optional blackout windows
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className={styles.errorAlert} role="alert">
          <span className={styles.errorIcon}>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className={styles.successAlert} role="status">
          <span className={styles.successIcon}>✓</span>
          <span>{successMessage}</span>
        </div>
      )}

      {/* Cron Expression Input */}
      <div className={styles.formGroup}>
        <label htmlFor="cron" className={styles.label}>
          Cron Expression <span className={styles.required}>*</span>
        </label>
        <input
          id="cron"
          type="text"
          className={styles.input}
          value={cronExpr}
          onChange={(e) => setCronExpr(e.target.value)}
          placeholder="0 2 * * *"
          required
          spellCheck="false"
          aria-describedby="cron-help"
        />
        <div id="cron-help" className={styles.helpText}>
          Standard 5-part cron syntax: minute hour day month day-of-week
          <br />
          Examples: <code>0 2 * * *</code> (daily at 2 AM) • <code>0 */6 * * *</code> (every 6 hours) • <code>0 0 * * MON</code> (Mondays at midnight)
        </div>
      </div>

      {/* Timezone Selection */}
      <div className={styles.formGroup}>
        <label htmlFor="timezone" className={styles.label}>
          Timezone <span className={styles.required}>*</span>
        </label>
        <select
          id="timezone"
          className={styles.select}
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          aria-describedby="timezone-help"
        >
          <optgroup label="Common Timezones">
            {commonTimezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </optgroup>
        </select>
        <div id="timezone-help" className={styles.helpText}>
          All cron times and blackout windows are evaluated in this timezone
        </div>
      </div>

      {/* Blackout Window Configuration */}
      <div className={styles.formGroup}>
        <label className={styles.label}>
          Blackout Window <span className={styles.optional}>(Optional)</span>
        </label>
        <p className={styles.description}>
          Scans scheduled during this time window will be automatically skipped. Useful for maintenance windows or business hours.
        </p>
        <div className={styles.timeRangeContainer}>
          <div className={styles.timeInput}>
            <label htmlFor="blackout-start" className={styles.timeLabel}>
              Start Time
            </label>
            <input
              id="blackout-start"
              type="time"
              className={styles.timeField}
              value={blackoutStart}
              onChange={(e) => setBlackoutStart(e.target.value)}
              aria-describedby="blackout-start-help"
            />
            <div id="blackout-start-help" className={styles.helpText}>
              HH:MM format (24-hour)
            </div>
          </div>

          <div className={styles.separator}>to</div>

          <div className={styles.timeInput}>
            <label htmlFor="blackout-end" className={styles.timeLabel}>
              End Time
            </label>
            <input
              id="blackout-end"
              type="time"
              className={styles.timeField}
              value={blackoutEnd}
              onChange={(e) => setBlackoutEnd(e.target.value)}
              aria-describedby="blackout-end-help"
            />
            <div id="blackout-end-help" className={styles.helpText}>
              HH:MM format (24-hour). Windows that cross midnight (e.g., 23:00–06:00) are supported.
            </div>
          </div>
        </div>
      </div>

      {/* Form Actions */}
      <div className={styles.formActions}>
        <button
          type="submit"
          className={styles.submitButton}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Saving...' : 'Save Schedule'}
        </button>
        {onCancel && (
          <button
            type="button"
            className={styles.cancelButton}
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
};

export default ScanScheduleForm;
