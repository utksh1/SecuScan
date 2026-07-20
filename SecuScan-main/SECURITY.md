# Security Policy

SecuScan is intended for authorized, ethical security testing and learning workflows. If you discover a vulnerability in SecuScan itself, please report it responsibly so it can be fixed without putting users at risk.

## Supported Code Lines

We currently provide security fixes on a best-effort basis for:

| Code Line | Status |
| --- | --- |
| `main` | Supported |
| Most recent release or snapshot | Best effort |
| Older forks, stale branches, or heavily modified local copies | Not guaranteed |

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues or pull requests.

Preferred disclosure path:

1. Use GitHub's private vulnerability reporting flow for this repository, if it is enabled.
2. If private reporting is not available, contact the maintainer directly through GitHub.

Please include as much detail as you can:

- Affected branch, commit, or version
- Clear reproduction steps
- Expected impact
- Logs, screenshots, or proof of concept if safe to share
- Any suggested mitigation if you already have one

## What Belongs in a Security Report

- Vulnerabilities in the SecuScan backend, frontend, or plugin loading system
- Authentication, authorization, secrets handling, or encryption issues
- Unsafe file handling, path traversal, injection, or remote execution risks
- Findings that expose user data, scan artifacts, or stored credentials

## What Does Not Belong in a Security Report

- Vulnerabilities in third-party targets scanned with SecuScan
- General support questions or setup problems
- Feature requests without a security impact
- Issues that only exist in unofficial forks unless they can be reproduced here

## Response Expectations

We aim to:

- Acknowledge a report within 72 hours
- Triage severity and reproduction details as quickly as possible
- Share status updates when a fix or mitigation is being prepared
- Credit reporters when appropriate and when they want to be acknowledged

Thank you for helping keep SecuScan safer for everyone using it responsibly.
