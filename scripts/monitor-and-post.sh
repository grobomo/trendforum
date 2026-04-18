#!/bin/bash
# Run the Claude Code monitor and post summary to Slack DM if there's output
SUMMARY_FILE="/tmp/claude-monitor-summary.txt"
rm -f "$SUMMARY_FILE"

cd /home/ubu/.openclaw/workspace
python3 scripts/monitor-claude-project.py 2>/dev/null

if [ -f "$SUMMARY_FILE" ] && [ -s "$SUMMARY_FILE" ]; then
    # Post to Slack DM via openclaw CLI
    SUMMARY=$(cat "$SUMMARY_FILE")
    # Use curl to hit the OpenClaw gateway API to send a Slack message
    curl -sf -X POST http://127.0.0.1:18789/v1/messages \
        -H "Content-Type: application/json" \
        -d "$(python3 -c "
import json, sys
summary = open('$SUMMARY_FILE').read()
print(json.dumps({
    'channel': 'slack',
    'target': 'D0ATWPM4DTK',
    'message': summary
}))
")" 2>/dev/null || true
    rm -f "$SUMMARY_FILE"
fi
