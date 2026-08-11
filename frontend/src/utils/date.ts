
export function parseDateSafe(rawValue: string | null | undefined): Date | null {
  if (!rawValue) return null
  const raw = rawValue.trim()
  if (!raw) return null
  if (raw.toLowerCase() === 'now') return new Date()

  try {
    const isoCompatible = raw.includes('T') ? raw : raw.replace(' ', 'T')

    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(isoCompatible)

    const candidates = hasTimezone
      ? [isoCompatible, raw]
      : [`${isoCompatible}Z`, isoCompatible, raw]

    for (const candidate of candidates) {
      const d = new Date(candidate)
      const isValid = !Number.isNaN(d.getTime())

      if (isValid && d.getFullYear() > 1900 && d.getFullYear() < 2100) {
        return d
      }
    }
  } catch (error) {
    console.error('Date parsing failed:', error, raw)
  }

  return null
}


function getPreferredTimeZone(): string | undefined {
  try {
    const saved = localStorage.getItem('secuscan-config')
    if (saved) {
      const config = JSON.parse(saved)
      if (config.timezone && config.timezone !== 'auto') {
        return config.timezone
      }
    }
  } catch (e) {
  }
  return undefined
}


export function getCurrentTimeZone(): string {
  const preferred = getPreferredTimeZone()
  if (preferred) return preferred
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch (e) {
    return 'UTC'
  }
}


export function getTimeZoneAbbreviation(): string {
  try {
    const tz = getPreferredTimeZone()
    const formatter = new Intl.DateTimeFormat([], {
        timeZoneName: 'short',
        ...(tz ? { timeZone: tz } : {})
    })
    const parts = formatter.formatToParts(new Date())
    const tzPart = parts.find(part => part.type === 'timeZoneName')
    return tzPart ? tzPart.value : ''
  } catch (e) {
    return ''
  }
}


export function formatBriefingDate(dateStr: string | null): string {
  const d = parseDateSafe(dateStr)
  if (!d) return ''

  const tz = getPreferredTimeZone()
  const options: Intl.DateTimeFormatOptions = tz ? { timeZone: tz } : {}

  const day = d.toLocaleDateString([], { ...options, day: '2-digit' })
  const month = d.toLocaleDateString([], { ...options, month: 'short' }).toUpperCase()
  const year = d.toLocaleDateString([], { ...options, year: '2-digit' })
  const time = d.toLocaleTimeString([], { ...options, hour: '2-digit', minute: '2-digit', hour12: false })

  return `${day} ${month}, ${year}, ${time}`
}


export function formatTaskInit(dateStr: string): { date: string, time: string, tz: string } {
  const parsed = parseDateSafe(dateStr)
  if (!parsed) return { date: 'UNKNOWN DATE', time: 'UNKNOWN TIME', tz: '' }

  const tz = getPreferredTimeZone()
  const date = parsed.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...(tz ? { timeZone: tz } : {})
  }).toUpperCase()

  const time = parsed.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    ...(tz ? { timeZone: tz } : {})
  })

  const tzAbbr = getTimeZoneAbbreviation()

  return { date, time, tz: tzAbbr }
}


export function formatDateLong(dateStr: string | null): string {
    const d = parseDateSafe(dateStr)
    if (!d) return 'N/A'

    const tz = getPreferredTimeZone()
    const formatted = d.toLocaleString([], {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        ...(tz ? { timeZone: tz } : {})
    }).toUpperCase()

    const tzAbbr = getTimeZoneAbbreviation()
    return tzAbbr ? `${formatted} ${tzAbbr}` : formatted
}


export function formatLocaleDateTime(
    dateStr: string | Date | null | undefined, 
    options: Intl.DateTimeFormatOptions = {}, 
    timeOnly = false
): string {
    const d = typeof dateStr === 'string' || dateStr === null || dateStr === undefined ? parseDateSafe(dateStr) : dateStr
    if (!d) return 'N/A'
    const tz = getPreferredTimeZone()
    const method = timeOnly ? 'toLocaleTimeString' : 'toLocaleDateString'
    return d[method]([], { ...(tz ? { timeZone: tz } : {}), ...(timeOnly ? { hour12: false } : {}), ...options })
}

export const formatLocaleDate = (dateStr: string | Date | null | undefined, options: Intl.DateTimeFormatOptions = {}) => 
    formatLocaleDateTime(dateStr, options, false)

export const formatLocaleTime = (dateStr: string | Date | null | undefined, options: Intl.DateTimeFormatOptions = {}) => 
    formatLocaleDateTime(dateStr, options, true)

export function formatDuration(seconds?: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) return 'N/A'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs.toString().padStart(2, '0')}s`
}


export type DateRange = 'all' | '24h' | '7d' | '30d'

export function isWithinDateRange(dateStr: string, range: DateRange): boolean {
  if (range === 'all') return true
  const d = parseDateSafe(dateStr)
  if (!d) return false
  const msMap = { '24h': 86400000, '7d': 604800000, '30d': 2592000000 }
  const diff = Date.now() - d.getTime()
  return diff >= 0 && diff <= msMap[range]
}