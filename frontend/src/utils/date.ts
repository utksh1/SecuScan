/**
 * Safe date parsing utility that handles ISO-8601 strings and raw SQLite strings.
 */
export function parseDateSafe(rawValue: string | null | undefined): Date | null {
  if (!rawValue) return null
  const raw = rawValue.trim()
  if (!raw) return null
  if (raw.toLowerCase() === 'now') return new Date()

  try {
    // Handle formats like "YYYY-MM-DD HH:MM:SS" (SQLite) vs standard ISO-8601
    const isoCompatible = raw.includes('T') ? raw : raw.replace(' ', 'T')
    
    // Check if the string already has timezone info (e.g. "Z" or "+HH:MM")
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(isoCompatible)
    
    // We try multiple candidate strings if timezone is missing
    const candidates = hasTimezone
      ? [isoCompatible, raw]
      : [`${isoCompatible}Z`, isoCompatible, raw]

    for (const candidate of candidates) {
      const d = new Date(candidate)
      if (!Number.isNaN(d.getTime())) return d
    }
  } catch (error) {
    console.error('Date parsing failed:', error, raw)
  }
  
  return null
}

/**
 * Gets the preferred timezone from local storage or returns undefined to use system default.
 */
function getPreferredTimeZone(): string | undefined {
    try {
        const saved = localStorage.getItem('secuscan-config');
        if (saved) {
            const config = JSON.parse(saved);
            if (config.timezone && config.timezone !== 'auto') {
                return config.timezone;
            }
        }
    } catch (e) {
        // Fallback to system default
    }
    return undefined;
}

/**
 * Returns the current timezone being used (either preferred or system default).
 */
export function getCurrentTimeZone(): string {
  const preferred = getPreferredTimeZone();
  if (preferred) return preferred;
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch (e) {
    return 'UTC'
  }
}

/**
 * Returns the short timezone abbreviation (e.g., IST, GMT) based on current timezone settings.
 */
export function getTimeZoneAbbreviation(): string {
  try {
    const tz = getPreferredTimeZone();
    const formatter = new Intl.DateTimeFormat([], { 
        timeZoneName: 'short',
        ...(tz ? { timeZone: tz } : {})
    });
    const parts = formatter.formatToParts(new Date());
    const tzPart = parts.find(part => part.type === 'timeZoneName');
    return tzPart ? tzPart.value : '';
  } catch (e) {
    return '';
  }
}

/**
 * Centralized formatting for the Dashboard's briefing date.
 */
export function formatBriefingDate(dateStr: string | null): string {
  const d = parseDateSafe(dateStr)
  if (!d) return ''
  
  const tz = getPreferredTimeZone();
  const options: Intl.DateTimeFormatOptions = tz ? { timeZone: tz } : {};
  
  const day = d.toLocaleDateString([], { ...options, day: '2-digit' })
  const month = d.toLocaleDateString([], { ...options, month: 'short' }).toUpperCase()
  const year = d.toLocaleDateString([], { ...options, year: '2-digit' })
  const time = d.toLocaleTimeString([], { ...options, hour: '2-digit', minute: '2-digit', hour12: false })
  
  return `${day} ${month}, ${year}, ${time}`
}

/**
 * Split date/time formatting used for task cards.
 */
export function formatTaskInit(dateStr: string): { date: string, time: string, tz: string } {
  const parsed = parseDateSafe(dateStr)
  if (!parsed) return { date: 'UNKNOWN DATE', time: 'UNKNOWN TIME', tz: '' }
  
  const tz = getPreferredTimeZone();
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
  
  const tzAbbr = getTimeZoneAbbreviation();
  
  return { date, time, tz: tzAbbr }
}

/**
 * Long format used in Reports and TaskDetails.
 */
export function formatDateLong(dateStr: string | null): string {
    const d = parseDateSafe(dateStr)
    if (!d) return 'N/A'
    
    const tz = getPreferredTimeZone();
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
    
    const tzAbbr = getTimeZoneAbbreviation();
    return tzAbbr ? `${formatted} ${tzAbbr}` : formatted;
}

/**
 * Shorthand for general toLocaleDateString without hardcoding.
 */
export function formatLocaleDate(dateStr: string | Date | null | undefined, options: Intl.DateTimeFormatOptions = {}): string {
    const d = typeof dateStr === 'string' || dateStr === null || dateStr === undefined ? parseDateSafe(dateStr) : dateStr;
    if (!d) return 'N/A';
    const tz = getPreferredTimeZone();
    return d.toLocaleDateString([], {
        ...(tz ? { timeZone: tz } : {}),
        ...options
    });
}

/**
 * Shorthand for general toLocaleTimeString without hardcoding.
 */
export function formatLocaleTime(dateStr: string | Date | null | undefined, options: Intl.DateTimeFormatOptions = {}): string {
    const d = typeof dateStr === 'string' || dateStr === null || dateStr === undefined ? parseDateSafe(dateStr) : dateStr;
    if (!d) return 'N/A';
    const tz = getPreferredTimeZone();
    return d.toLocaleTimeString([], {
        ...(tz ? { timeZone: tz } : {}),
        hour12: false,
        ...options
    });
}
