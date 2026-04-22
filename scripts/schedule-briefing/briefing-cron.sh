#!/bin/bash
# Schedule Briefing Cron
# Runs hourly, gathers all 5 sources, posts to main session for analysis.
# The agent receives the raw data and synthesizes the briefing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_FILE="/tmp/schedule-briefing-latest.json"
LOG_FILE="/tmp/schedule-briefing.log"

echo "$(date -Iseconds) Starting schedule briefing gather..." >> "$LOG_FILE"

# Run the gatherer
python3 "$SCRIPT_DIR/gather.py" > "$OUTPUT_FILE" 2>> "$LOG_FILE"

if [ $? -ne 0 ]; then
    echo "$(date -Iseconds) ERROR: gather.py failed" >> "$LOG_FILE"
    exit 1
fi

# Get file size
SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "0")
echo "$(date -Iseconds) Gathered $SIZE bytes" >> "$LOG_FILE"

echo "$(date -Iseconds) Done. Data saved to $OUTPUT_FILE" >> "$LOG_FILE"
