import React, { useState } from 'react'

export interface SchedulePayload {
  cron_expression: string
  timezone: string
  blackout_start: string | null
  blackout_end: string | null
}

interface ScanScheduleFormProps {
  onSubmit: (payload: SchedulePayload) => Promise<void>
  onCancel?: () => void
  embedded?: boolean
  initialValues?: Partial<SchedulePayload>
  submitLabel?: string
}

interface ValidationResult {
  valid: boolean
  message?: string
}

const commonTimezones = [
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
  'Australia/Melbourne',
]

function validateCron(cron: string): ValidationResult {
  if (!cron.trim()) {
    return { valid: false, message: 'Cron expression is required.' }
  }
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) {
    return {
      valid: false,
      message: `Invalid cron expression. Must contain exactly 5 fields, found ${parts.length}.`,
    }
  }
  if (parts.some(part => !part)) {
    return { valid: false, message: 'Cron expression contains empty fields.' }
  }
  return { valid: true }
}

function validateTimeFormat(timeStr: string): boolean {
  if (!timeStr) return true
  return /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/.test(timeStr)
}

export default function ScanScheduleForm({
  onSubmit,
  onCancel,
  embedded = false,
  initialValues,
  submitLabel = 'Save Schedule',
}: ScanScheduleFormProps) {
  const [cronExpr, setCronExpr] = useState(initialValues?.cron_expression ?? '0 2 * * *')
  const [timezone, setTimezone] = useState(initialValues?.timezone ?? 'UTC')
  const [blackoutStart, setBlackoutStart] = useState(initialValues?.blackout_start ?? '')
  const [blackoutEnd, setBlackoutEnd] = useState(initialValues?.blackout_end ?? '')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const inputClass =
    'w-full bg-charcoal-dark border-4 border-black px-4 py-3 text-sm text-silver-bright placeholder:text-silver/30 focus:outline-none focus:border-rag-red transition-colors'
  const labelClass =
    'text-[10px] font-black text-silver-bright uppercase tracking-[0.2em]'

  function validateBlackoutWindow(): ValidationResult {
    const hasStart = Boolean(blackoutStart.trim())
    const hasEnd = Boolean(blackoutEnd.trim())
    if (hasStart !== hasEnd) {
      return {
        valid: false,
        message: 'Both start and end times must be provided for a blackout window.',
      }
    }
    if (hasStart && !validateTimeFormat(blackoutStart)) {
      return { valid: false, message: 'Blackout start time must be in HH:MM format.' }
    }
    if (hasEnd && !validateTimeFormat(blackoutEnd)) {
      return { valid: false, message: 'Blackout end time must be in HH:MM format.' }
    }
    return { valid: true }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')

    const cronValidation = validateCron(cronExpr)
    if (!cronValidation.valid) {
      setError(cronValidation.message || '')
      return
    }

    const blackoutValidation = validateBlackoutWindow()
    if (!blackoutValidation.valid) {
      setError(blackoutValidation.message || 'Invalid blackout window configuration.')
      return
    }

    const payload: SchedulePayload = {
      cron_expression: cronExpr.trim(),
      timezone,
      blackout_start: blackoutStart || null,
      blackout_end: blackoutEnd || null,
    }

    setIsSubmitting(true)
    try {
      await onSubmit(payload)
      if (!embedded) {
        setCronExpr('0 2 * * *')
        setTimezone('UTC')
        setBlackoutStart('')
        setBlackoutEnd('')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save schedule.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={embedded ? 'space-y-6' : 'space-y-8'}>
      {!embedded && (
        <div className="space-y-2">
          <h2 className="text-xl font-black text-silver-bright uppercase tracking-tight">
            Configure Recurring Scan
          </h2>
          <p className="text-[11px] text-silver/50 uppercase tracking-widest font-black">
            Cron scheduling with IANA timezone support and optional blackout windows
          </p>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="border-4 border-black bg-rag-red/20 px-4 py-3 text-[10px] font-black uppercase tracking-widest text-rag-red"
        >
          {error}
        </div>
      )}

      <div className="space-y-2">
        <label htmlFor="cron" className={labelClass}>
          Cron Expression
        </label>
        <input
          id="cron"
          type="text"
          className={`${inputClass} font-mono`}
          value={cronExpr}
          onChange={e => setCronExpr(e.target.value)}
          placeholder="0 2 * * *"
          required
          spellCheck={false}
          aria-describedby="cron-help"
        />
        <p id="cron-help" className="text-[10px] text-silver/40 uppercase tracking-widest">
          5-part cron syntax: minute hour day month day-of-week (e.g. 0 2 * * *)
        </p>
      </div>

      <div className="space-y-2">
        <label htmlFor="timezone" className={labelClass}>
          Timezone
        </label>
        <select
          id="timezone"
          className={inputClass}
          value={timezone}
          onChange={e => setTimezone(e.target.value)}
          aria-describedby="timezone-help"
        >
          {commonTimezones.map(tz => (
            <option key={tz} value={tz}>
              {tz}
            </option>
          ))}
        </select>
        <p id="timezone-help" className="text-[10px] text-silver/40 uppercase tracking-widest">
          Cron times and blackout windows use this IANA timezone
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-1">
          <span className={labelClass}>Blackout Window (Optional)</span>
          <p className="text-[10px] text-silver/40 uppercase tracking-widest">
            Scans due during this window are skipped
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-end">
          <div className="space-y-2">
            <label htmlFor="blackout-start" className="text-[9px] font-black text-silver/50 uppercase tracking-widest">
              Start
            </label>
            <input
              id="blackout-start"
              type="time"
              className={inputClass}
              value={blackoutStart}
              onChange={e => setBlackoutStart(e.target.value)}
            />
          </div>
          <span className="text-[10px] font-black text-silver/40 uppercase tracking-widest pb-3">to</span>
          <div className="space-y-2">
            <label htmlFor="blackout-end" className="text-[9px] font-black text-silver/50 uppercase tracking-widest">
              End
            </label>
            <input
              id="blackout-end"
              type="time"
              className={inputClass}
              value={blackoutEnd}
              onChange={e => setBlackoutEnd(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="flex-1 border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 bg-silver-bright border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all disabled:opacity-40"
        >
          {isSubmitting ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  )
}
