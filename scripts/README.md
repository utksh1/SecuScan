# GitHub Issue Management Scripts

This directory contains scripts to help manage GitHub issues for the SecuScan repository.

## Scripts

### 1. `assign_issues.sh`
Automatically assigns issues to contributors based on recent comments requesting assignment.

**Features:**
- Respects the 5-issue limit per contributor
- Only assigns issues where users have requested assignment
- Filters issues with recent activity (last 5 days)
- Provides a review before making assignments

**Usage:**
```bash
./scripts/assign_issues.sh
```

### 2. `close_low_quality_issues.sh`
Identifies and helps close low-quality or spam issues.

**Features:**
- Detects very short/empty bodies
- Identifies spam keywords (hiring, crypto scams, etc.)
- Allows review before closing
- Supports individual or batch closing

**Usage:**
```bash
./scripts/close_low_quality_issues.sh
```

## Assignment Summary (2026-07-20)

**Total Issues Assigned: 52**

Successfully assigned issues to contributors who had shown interest by commenting, while respecting the 5-issue limit for each contributor.

### Distribution:
- **35 unique contributors** received assignments
- **10 contributors** now at the 5-issue limit
- **77 issues** still have comments but are unassigned (mostly from users already at limit)

### Contributors at 5-issue limit:
- tmdeveloper007
- shravanithouta108
- karrisanthoshigayatri
- ionfwsrijan
- anshikaagr
- advikdivekar
- aaniya22
- Somil450
- Shikhar-404exe
- Rakshak05

## Tips

1. Run `assign_issues.sh` regularly (daily or after batch PR merges) to assign new issues
2. Contributors who complete their assigned issues will automatically become available for new assignments
3. The scripts use `gh` CLI and `jq` for reliability and performance
4. All assignments are logged and can be reviewed before confirmation

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- `jq` for JSON processing
- Bash 3.2+ (macOS compatible)
