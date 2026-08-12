#!/bin/bash
# GitHub Issue Management Master Script for SecuScan
# Provides an interactive menu for common issue management tasks

set -e

REPO="utksh1/SecuScan"

show_menu() {
    clear
    echo "═══════════════════════════════════════════════════"
    echo "  SecuScan GitHub Issue Management"
    echo "═══════════════════════════════════════════════════"
    echo
    echo "1) Auto-assign issues (respects 5-issue limit)"
    echo "2) Check assignment statistics"
    echo "3) Find unassigned issues with activity"
    echo "4) Close low-quality/spam issues"
    echo "5) Check users at 5-issue limit"
    echo "6) Bulk check contributor availability"
    echo "7) Exit"
    echo
    read -p "Select an option [1-7]: " choice
}

auto_assign() {
    echo "Running auto-assignment script..."
    ./scripts/assign_issues.sh
}

check_stats() {
    echo "═══ Assignment Statistics ═══"
    echo
    echo "Total open issues:"
    gh issue list --repo "$REPO" --state open --limit 1 --json number --jq 'length' | xargs -I {} echo "  {}"
    
    echo
    echo "Unassigned issues:"
    gh issue list --repo "$REPO" --state open --limit 1000 --json assignees --jq '[.[] | select(.assignees | length == 0)] | length'
    
    echo
    echo "Issues with comments but unassigned:"
    gh issue list --repo "$REPO" --state open --limit 1000 --json assignees,comments --jq '[.[] | select(.assignees | length == 0) | select(.comments | length > 0)] | length'
    
    echo
    echo "Top 10 most active assignees:"
    gh issue list --repo "$REPO" --limit 1000 --state open --json assignees \
      --jq '.[] | .assignees[].login' | sort | uniq -c | sort -rn | head -10 | \
      awk '{printf "  %-30s %d issues\n", $2, $1}'
    
    echo
    read -p "Press Enter to continue..."
}

find_unassigned() {
    echo "═══ Unassigned Issues with Recent Activity ═══"
    echo
    gh issue list --repo "$REPO" --state open --limit 100 --json number,title,assignees,comments,updatedAt \
      --jq '.[] | select(.assignees | length == 0) | select(.comments | length > 0) | select(.updatedAt | fromdateiso8601 > (now - 432000)) | "#\(.number): \(.title[0:70])... (\(.comments | length) comments)"'
    echo
    read -p "Press Enter to continue..."
}

close_spam() {
    echo "Running spam detection script..."
    ./scripts/close_low_quality_issues.sh
}

check_limits() {
    echo "═══ Contributors at 5-issue Limit ═══"
    echo
    gh issue list --repo "$REPO" --limit 1000 --state open --json assignees \
      --jq '.[] | .assignees[].login' | sort | uniq -c | sort -rn | \
      awk '$1 >= 5 {printf "  %-30s %d issues\n", $2, $1}'
    echo
    read -p "Press Enter to continue..."
}

check_availability() {
    echo "═══ Check Contributor Availability ═══"
    echo
    read -p "Enter usernames (space-separated): " usernames
    
    for user in $usernames; do
        count=$(gh issue list --repo "$REPO" --assignee "$user" --state open --limit 10 --json number --jq '. | length' 2>/dev/null || echo "0")
        if [ "$count" -lt 5 ]; then
            printf "%-30s %d/5 (Available: %d slots)\n" "$user" "$count" "$((5-count))"
        else
            printf "%-30s %d/5 (AT LIMIT)\n" "$user" "$count"
        fi
    done
    
    echo
    read -p "Press Enter to continue..."
}

# Main loop
while true; do
    show_menu
    case $choice in
        1) auto_assign ;;
        2) check_stats ;;
        3) find_unassigned ;;
        4) close_spam ;;
        5) check_limits ;;
        6) check_availability ;;
        7) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option. Press Enter to continue..."; read ;;
    esac
done
