#!/usr/bin/env bash
# Sync hook monitor state to Trello Lessons board
# Reads hook-monitor.json and updates/creates Trello cards
# Run periodically or after hook status changes

set -euo pipefail

HOOKS_MONITOR="$HOME/.openclaw/workspace/memory/hooks/hook-monitor.json"
CENTRAL_LOG="$HOME/.openclaw/workspace/memory/hooks/central.log"

TRELLO_KEY=$(python3 -c "import keyring; print(keyring.get_password('openclaw','TRELLO_API_KEY'))" 2>/dev/null || echo "")
TRELLO_TOKEN=$(python3 -c "import keyring; print(keyring.get_password('openclaw','TRELLO_TOKEN'))" 2>/dev/null || echo "")

if [[ -z "$TRELLO_KEY" || "$TRELLO_KEY" == "None" ]]; then
  echo "ERROR: Trello creds not available"
  exit 1
fi

# Lessons board lists
INBOX="69e3e694635b28132b1ab3e9"
TECHNICAL="69e3e694fe89c3d1e8e1f274"
APPLIED="69e3e693800309fd278f4b22"

# Labels
LABEL_APPLIED="green"
LABEL_IN_PROGRESS="yellow"
LABEL_HARD_WAY="red"
LABEL_INSIGHT="blue"

if [[ ! -f "$HOOKS_MONITOR" ]]; then
  echo "No hook monitor file found"
  exit 0
fi

# Parse hooks and generate summary
python3 << 'PYEOF'
import json
import sys
import os

monitor_path = os.path.expanduser("~/.openclaw/workspace/memory/hooks/hook-monitor.json")
log_path = os.path.expanduser("~/.openclaw/workspace/memory/hooks/central.log")

with open(monitor_path) as f:
    data = json.load(f)

hooks = data.get("hooks", {})
meta = data.get("meta", {})

print(f"=== Hook Monitor Summary ===")
print(f"Total hooks: {meta.get('total_hooks', len(hooks))}")
print(f"Last review: {meta.get('last_review', 'never')}")
print()

for name, info in hooks.items():
    status = info.get("status", "unknown")
    fires = info.get("fire_count", 0)
    blocks = info.get("block_count", 0)
    expires = info.get("monitoring_expires", "?")
    print(f"  [{status}] {name}: {fires} fires, {blocks} blocks (monitoring until {expires})")

# Count log entries if log exists
if os.path.exists(log_path):
    with open(log_path) as f:
        lines = f.readlines()
    print(f"\nCentral log: {len(lines)} entries")
else:
    print(f"\nCentral log: no entries yet")
PYEOF

echo ""
echo "Trello sync complete."
