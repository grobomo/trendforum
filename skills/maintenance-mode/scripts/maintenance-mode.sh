#!/bin/bash
# Maintenance Mode — Mechanical layer for state preservation
#
# WHY: The LLM agent does semantic analysis to identify noise sources.
# This script does the dumb reliable parts: backup, stop, restore.
#
# The agent gathers system state, classifies what's noise vs essential,
# writes the service list to systemd-services.json, then calls this script.
#
# Usage:
#   maintenance-mode.sh save     # Backup crontab + OpenClaw crons (agent writes services JSON)
#   maintenance-mode.sh stop     # Stop services from JSON + disable crons + clear crontab
#   maintenance-mode.sh exit     # Restore exact pre-maintenance state
#   maintenance-mode.sh status   # Show current state

set -euo pipefail

STATE_DIR="$HOME/.openclaw/maintenance-state"
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
FLAG_FILE="$WORKSPACE/MAINTENANCE_MODE.md"
CRONTAB_BACKUP="$STATE_DIR/crontab.bak"
SERVICES_BACKUP="$STATE_DIR/systemd-services.json"
CRONS_BACKUP="$STATE_DIR/openclaw-crons.json"

log() { echo "[maintenance] $(date '+%H:%M:%S') $*"; }

cmd_save() {
    mkdir -p "$STATE_DIR"
    log "Saving pre-maintenance state..."

    # 1. Crontab
    if crontab -l > "$CRONTAB_BACKUP" 2>/dev/null; then
        log "  Crontab: $(wc -l < "$CRONTAB_BACKUP") lines saved"
    else
        echo "# empty" > "$CRONTAB_BACKUP"
        log "  Crontab: empty"
    fi

    # 2. OpenClaw crons (if openclaw is installed)
    if command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True, timeout=15)
crons = []
for line in result.stdout.strip().splitlines():
    parts = line.split()
    if parts and len(parts[0]) >= 36 and parts[0].count('-') == 4:
        entry = {'id': parts[0], 'was_enabled': 'disabled' not in line.lower()}
        if len(parts) > 1:
            entry['name'] = parts[1]
        crons.append(entry)

with open(sys.argv[1], 'w') as f:
    json.dump(crons, f, indent=2)
print(f"  OpenClaw crons: {len(crons)} entries saved")
PYEOF
    else
        echo "[]" > "$CRONS_BACKUP"
        log "  openclaw not installed, skipping crons"
    fi

    # 3. Timestamp
    date -Iseconds > "$STATE_DIR/entered-at.txt"

    # 4. Remind agent to write systemd-services.json
    if [ ! -f "$SERVICES_BACKUP" ]; then
        log ""
        log "  ⚠️  Write $SERVICES_BACKUP with services to stop."
        log "  Format: {\"service-name\": {\"active\": \"active\", \"enabled\": \"enabled\"}, ...}"
        log "  Only include services YOU classified as noise sources."
    else
        log "  Services JSON already exists ($(python3 -c "import json; print(len(json.load(open('$SERVICES_BACKUP'))))" 2>/dev/null || echo '?') entries)"
    fi

    log "State saved to $STATE_DIR"
}

cmd_stop() {
    log "Stopping noise sources..."

    # 1. Stop systemd services listed in JSON
    if [ -f "$SERVICES_BACKUP" ]; then
        python3 - "$SERVICES_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    services = json.load(f)

for svc, info in services.items():
    svc_name = f'{svc}.service'
    if info.get('active') == 'active':
        result = subprocess.run(
            ['systemctl', '--user', 'stop', svc_name],
            capture_output=True, text=True, timeout=10
        )
        status = 'stopped' if result.returncode == 0 else f'failed ({result.stderr.strip()})'
    else:
        status = 'already inactive'
    print(f"  {svc}: {status}")
PYEOF
    else
        log "  No services JSON found — skipping systemd services"
    fi

    # 2. Disable OpenClaw crons
    if [ -f "$CRONS_BACKUP" ] && command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    crons = json.load(f)

count = 0
for cron in crons:
    cid = cron.get('id', '')
    if cid and cron.get('was_enabled', True):
        subprocess.run(['openclaw', 'cron', 'disable', cid],
                       capture_output=True, text=True, timeout=10)
        count += 1
        name = cron.get('name', cid[:12])
        print(f"  Disabled: {name}")

print(f"  Total: {count} crons disabled")
PYEOF
    fi

    # 3. Clear crontab
    echo "# MAINTENANCE MODE - entered $(date)" | crontab -
    log "  Crontab cleared"

    log "=== MAINTENANCE MODE ACTIVE ==="
}

cmd_exit() {
    if [ ! -d "$STATE_DIR" ]; then
        log "ERROR: No saved state at $STATE_DIR"
        exit 1
    fi

    log "Restoring pre-maintenance state..."
    [ -f "$STATE_DIR/entered-at.txt" ] && log "  Entered at: $(cat "$STATE_DIR/entered-at.txt")"

    # 1. Restore crontab
    if [ -f "$CRONTAB_BACKUP" ] && [ "$(cat "$CRONTAB_BACKUP")" != "# empty" ]; then
        crontab "$CRONTAB_BACKUP"
        log "  Crontab restored ($(crontab -l 2>/dev/null | wc -l) lines)"
    else
        crontab -r 2>/dev/null || true
        log "  Crontab was empty, cleared"
    fi

    # 2. Restore systemd services
    if [ -f "$SERVICES_BACKUP" ]; then
        python3 - "$SERVICES_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    services = json.load(f)

for svc, info in services.items():
    svc_name = f'{svc}.service'
    if info.get('enabled') == 'enabled':
        subprocess.run(['systemctl', '--user', 'enable', svc_name],
                       capture_output=True, timeout=10)
    if info.get('active') == 'active':
        result = subprocess.run(['systemctl', '--user', 'start', svc_name],
                       capture_output=True, text=True, timeout=10)
        status = 'started' if result.returncode == 0 else f'failed ({result.stderr.strip()})'
    else:
        status = f"was {info.get('active', '?')} — left alone"
    print(f"  {svc}: {status}")
PYEOF
        log "  Services restored"
    fi

    # 3. Re-enable OpenClaw crons
    if [ -f "$CRONS_BACKUP" ] && command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    crons = json.load(f)

count = 0
for cron in crons:
    cid = cron.get('id', '')
    if cid and cron.get('was_enabled', True):
        subprocess.run(['openclaw', 'cron', 'enable', cid],
                       capture_output=True, text=True, timeout=10)
        count += 1
        print(f"  Enabled: {cron.get('name', cid[:12])}")

print(f"  Total: {count} crons re-enabled")
PYEOF
        log "  Crons restored"
    fi

    # 4. Remove flag file
    rm -f "$FLAG_FILE"

    # 5. Archive state (never delete)
    mv "$STATE_DIR" "$STATE_DIR.last-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    log "  State archived"

    log "=== MAINTENANCE MODE EXITED ==="
}

cmd_status() {
    if [ -f "$FLAG_FILE" ]; then
        echo "MAINTENANCE MODE: ACTIVE"
        [ -f "$STATE_DIR/entered-at.txt" ] && echo "  Entered: $(cat "$STATE_DIR/entered-at.txt")"
        echo ""
        echo "Preserved state:"
        [ -f "$CRONTAB_BACKUP" ] && echo "  Crontab: $(wc -l < "$CRONTAB_BACKUP") lines"
        [ -f "$SERVICES_BACKUP" ] && echo "  Services: $(python3 -c "import json; d=json.load(open('$SERVICES_BACKUP')); print(', '.join(d.keys()))" 2>/dev/null || echo "saved")"
        [ -f "$CRONS_BACKUP" ] && echo "  Crons: $(python3 -c "import json; print(f'{len(json.load(open(\"$CRONS_BACKUP\")))} entries')" 2>/dev/null || echo "saved")"
    else
        echo "MAINTENANCE MODE: INACTIVE"
        archives=$(ls -d "$STATE_DIR".last-* 2>/dev/null | wc -l)
        [ "$archives" -gt 0 ] && echo "  Previous sessions: $archives archived"
    fi
}

case "${1:-status}" in
    save)   cmd_save ;;
    stop)   cmd_stop ;;
    exit)   cmd_exit ;;
    status) cmd_status ;;
    *)      echo "Usage: $0 {save|stop|exit|status}"; exit 1 ;;
esac
