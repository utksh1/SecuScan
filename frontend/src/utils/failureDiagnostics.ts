export type FailureCategory =
  | 'missing_binary'
  | 'invalid_target'
  | 'timeout'
  | 'parser_failure'
  | 'consent_blocked'
  | 'rate_limited'
  | 'command_rejected'
  | 'network_policy'
  | 'unknown'

export interface FailureDiagnostic {
  category: FailureCategory
  label: string
  guidance: string
  icon: string
}

const FAILURE_PATTERNS: Array<{
  patterns: RegExp[]
  category: FailureCategory
  label: string
  guidance: string
  icon: string
}> = [
  {
    patterns: [/not found/i, /no such file/i, /command not found/i, /binary.*not.*found/i, /requires.*external/i],
    category: 'missing_binary',
    label: 'Missing Binary',
    guidance: 'The required scanner binary is not installed or not in PATH. Check the system dependencies and ensure the tool is available on the backend server.',
    icon: 'construction',
  },
  {
    patterns: [/invalid target/i, /not a valid/i, /failed to resolve/i, /name or service not known/i, /no address associated/i],
    category: 'invalid_target',
    label: 'Invalid Target',
    guidance: 'The target could not be resolved or is not in a valid format. Verify the target IP, hostname, or URL and try again.',
    icon: 'link_off',
  },
  {
    patterns: [/timed out/i, /timeout/i, /no response/i, /connection.*tim/i, /read.*timed/i],
    category: 'timeout',
    label: 'Scan Timeout',
    guidance: 'The scan exceeded its time limit. Consider increasing the timeout in the engine parameters or narrowing the target scope.',
    icon: 'timer_off',
  },
  {
    patterns: [/parser.*fail/i, /parse.*error/i, /unexpected output/i, /could not parse/i, /malformed/i],
    category: 'parser_failure',
    label: 'Parser Failure',
    guidance: 'The tool produced output that the parser could not interpret. This may indicate an incompatible tool version or unexpected response format.',
    icon: 'bug_report',
  },
  {
    patterns: [/consent/i, /requires consent/i, /not granted/i, /consent.*required/i],
    category: 'consent_blocked',
    label: 'Consent Required',
    guidance: 'This tool requires explicit consent for the target. Enable consent in the tool configuration before launching.',
    icon: 'gavel',
  },
  {
    patterns: [/rate limit/i, /too many requests/i, /429/i, /rate.*limit/i],
    category: 'rate_limited',
    label: 'Rate Limited',
    guidance: 'The backend or external service is rate-limiting requests. Wait before retrying or reduce concurrent scan throughput.',
    icon: 'speed',
  },
  {
    patterns: [/unknown option/i, /flag provided but not defined/i, /invalid option/i, /unrecognized/i, /command.*rejected/i],
    category: 'command_rejected',
    label: 'Command Rejected',
    guidance: 'The tool rejected the provided command-line arguments. Check that the tool version supports the configured options.',
    icon: 'block',
  },
  {
    patterns: [/network policy/i, /denied access/i, /policy.*denied/i],
    category: 'network_policy',
    label: 'Network Policy Blocked',
    guidance: 'The network policy denied access to the target. Review the target whitelist and network policy configuration.',
    icon: 'shield_off',
  },
]

export function classifyFailure(errorMessage: string | null | undefined, exitCode: number | null | undefined, rawOutput?: string): FailureCategory {
  const text = [errorMessage, rawOutput].filter(Boolean).join('\n')
  for (const entry of FAILURE_PATTERNS) {
    for (const pattern of entry.patterns) {
      if (pattern.test(text)) {
        return entry.category
      }
    }
  }
  if (exitCode && exitCode > 0) {
    return 'unknown'
  }
  return 'unknown'
}

export function getFailureDiagnostic(errorMessage: string | null | undefined, exitCode: number | null | undefined, rawOutput?: string): FailureDiagnostic {
  const category = classifyFailure(errorMessage, exitCode, rawOutput)
  const entry = FAILURE_PATTERNS.find((e) => e.category === category)
  if (entry) {
    return { category: entry.category, label: entry.label, guidance: entry.guidance, icon: entry.icon }
  }
  return {
    category: 'unknown',
    label: 'Unknown Error',
    guidance: 'An unexpected error occurred. Check the raw output and error message for details, then consult the tool documentation.',
    icon: 'error',
  }
}
