#!/usr/bin/env bash
# Review hook monitoring status — outputs structured data for LLM analysis
# Called during session startup or heartbeat to review hook health
# Pipe output to Haiku for analysis decisions

set -euo pipefail

HOOKS_MONITOR="$HOME/.openclaw/workspace/memory/hooks/hook-monitor.json"
CENTRAL_LOG="$HOME/.openclaw/workspace/memory/hooks/central.log"
LESSONS_DIR="$HOME/.openclaw/workspace/memory/lessons"
TODAY=$(date +%Y-%m-%d)

echo "=== HOOK REVIEW — ${TODAY} ==="
echo ""

if [[ ! -f "$HOOKS_MONITOR" ]]; then
  echo "No hooks to review."
  exit 0
fi

# Hooks needing attention
python3 << PYEOF
import json
import os
from datetime import datetime, timedelta

monitor_path = os.path.expanduser("~/.openclaw/workspace/memory/hooks/hook-monitor.json")
log_path = os.path.expanduser("~/.openclaw/workspace/memory/hooks/central.log")
today = datetime.now().strftime("%Y-%m-%d")

with open(monitor_path) as f:
    data = json.load(f)

hooks = data.get("hooks", {})
alerts = []

for name, info in hooks.items():
    status = info.get("status", "unknown")
    fires = info.get("fire_count", 0)
    created = info.get("created", "")
    expires = info.get("monitoring_expires", "")
    
    # Alert: new hook with zero fires after 3+ days
    if status == "new" and fires == 0 and created:
        try:
            created_dt = datetime.strptime(created, "%Y-%m-%d")
            if (datetime.now() - created_dt).days >= 3:
                alerts.append(f"⚠️  {name}: NEW hook, 0 fires after {(datetime.now() - created_dt).days} days — likely bad trigger or overly narrow. Review original transcript and verify trigger logic.")
        except ValueError:
            pass
    
    # Alert: monitoring period expired
    if status == "new" and expires:
        try:
            exp_dt = datetime.strptime(expires, "%Y-%m-%d")
            if datetime.now() >= exp_dt:
                alerts.append(f"🔴 {name}: Monitoring period EXPIRED. Must evaluate: promote to verified, mark ineffective, or extend monitoring with fixes.")
        except ValueError:
            pass
    
    # Alert: harmful hook still active
    if status == "harmful":
        alerts.append(f"🚨 {name}: Marked HARMFUL — should be disabled immediately if not already.")

print("--- Hook Status ---")
for name, info in hooks.items():
    print(f"  {info.get('status','?'):12s} | {name:30s} | fires: {info.get('fire_count',0):3d} | blocks: {info.get('block_count',0):3d}")

if alerts:
    print("")
    print("--- Alerts ---")
    for a in alerts:
        print(f"  {a}")
else:
    print("")
    print("--- No alerts ---")

# Log tail
if os.path.exists(log_path):
    with open(log_path) as f:
        lines = f.readlines()
    recent = [l for l in lines[-20:]]
    if recent:
        print("")
        print("--- Recent Log (last 20) ---")
        for l in recent:
            print(f"  {l.rstrip()}")
PYEOF

echo ""
echo "=== END REVIEW ==="
