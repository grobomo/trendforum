#!/bin/bash
# Check Claude Code progress on teams-webhooks project
# Called by cron every 15 min

PROJECT="/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/teams-webhooks"

echo "=== teams-webhooks Claude Code Check ==="
echo "Time: $(date)"

# Git log - recent commits
echo ""
echo "## Recent Commits"
cd "$PROJECT" && git log --oneline -5 2>/dev/null || echo "No commits yet"

# TODO.md status - count checked vs unchecked
echo ""
echo "## TODO Status"
if [ -f "$PROJECT/TODO.md" ]; then
    DONE=$(grep -c '^\- \[x\]' "$PROJECT/TODO.md" 2>/dev/null || echo 0)
    TODO=$(grep -c '^\- \[ \]' "$PROJECT/TODO.md" 2>/dev/null || echo 0)
    echo "Done: $DONE | Remaining: $TODO"
    echo ""
    echo "## Next unchecked items:"
    grep '^\- \[ \]' "$PROJECT/TODO.md" | head -3
fi

# Check for specs output
echo ""
echo "## Specs created"
ls "$PROJECT/specs/" 2>/dev/null || echo "No specs/ dir yet"

# SESSION_STATE.md - last activity
echo ""
echo "## Session State"
if [ -f "$PROJECT/SESSION_STATE.md" ]; then
    head -5 "$PROJECT/SESSION_STATE.md"
else
    echo "No SESSION_STATE.md yet"
fi
