#!/bin/bash
# Teams poller cron handler
# Called by openclaw cron — polls for new Teams messages
# Outputs formatted prompt if new messages found, empty otherwise

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

python3 poll_teams.py 2>/tmp/teams-poller.log
