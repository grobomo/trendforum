#!/usr/bin/env bash
# Monitor hook-runner project for Coconut → Joel status updates
# Checks: git history, .coconut/STATUS_REPORT.md, TODO.md, uncommitted changes
# Runs via openclaw cron every 15 minutes

set -euo pipefail

PROJECT="/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/hook-runner"
COCONUT_DIR="$PROJECT/.coconut"
STATE_FILE="$HOME/.openclaw/workspace/memory/hook-runner-monitor-state.json"

# Ensure state dir exists
mkdir -p "$(dirname "$STATE_FILE")"

# Load last known commit
LAST_COMMIT=""
if [[ -f "$STATE_FILE" ]]; then
    LAST_COMMIT=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('last_commit',''))" 2>/dev/null || echo "")
fi

# Current state
cd "$PROJECT" 2>/dev/null || { echo "Project dir not found"; exit 0; }

CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
STATUS=$(git status --short 2>/dev/null | head -10)

# New commits since last check
NEW_COMMITS=""
if [[ -n "$LAST_COMMIT" && "$LAST_COMMIT" != "$CURRENT_COMMIT" ]]; then
    NEW_COMMITS=$(git log --oneline "$LAST_COMMIT"..HEAD --all 2>/dev/null | head -15)
fi

# If no last commit tracked, show last 5
if [[ -z "$LAST_COMMIT" ]]; then
    NEW_COMMITS=$(git log --oneline -5 --all 2>/dev/null)
fi

# Check for status report from Claude Code
STATUS_REPORT=""
if [[ -f "$COCONUT_DIR/STATUS_REPORT.md" ]]; then
    STATUS_REPORT=$(cat "$COCONUT_DIR/STATUS_REPORT.md" 2>/dev/null)
fi

# Check if request is still pending (not yet answered)
REQUEST_PENDING="false"
if [[ -f "$COCONUT_DIR/STATUS_REQUEST.md" ]]; then
    REQ_LINES=$(wc -l < "$COCONUT_DIR/STATUS_REQUEST.md")
    if [[ "$REQ_LINES" -gt 5 ]]; then
        REQUEST_PENDING="true"
    fi
fi

# Build report
echo "=== HOOK-RUNNER PROJECT MONITOR ==="
echo "Branch: $BRANCH"
echo "Latest commit: $CURRENT_COMMIT"
echo "Last tracked: ${LAST_COMMIT:-none}"
echo ""

if [[ -n "$NEW_COMMITS" ]]; then
    echo "--- New Commits ---"
    echo "$NEW_COMMITS"
    echo ""
fi

if [[ -n "$STATUS" ]]; then
    echo "--- Uncommitted Changes ---"
    echo "$STATUS"
    echo ""
fi

if [[ -n "$STATUS_REPORT" ]]; then
    echo "--- Claude Code Status Report ---"
    echo "$STATUS_REPORT"
    echo ""
fi

if [[ "$REQUEST_PENDING" == "true" ]]; then
    echo "--- Status Request: PENDING (not yet answered) ---"
    echo ""
fi

# Detect if anything changed
if [[ -z "$NEW_COMMITS" && -z "$STATUS" && -z "$STATUS_REPORT" ]]; then
    echo "No activity since last check."
fi

# Save state
python3 -c "
import json
state = {'last_commit': '$CURRENT_COMMIT', 'branch': '$BRANCH'}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null

echo "=== END ==="
