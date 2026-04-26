#!/bin/bash
# Maintenance Mode — Enter/Exit with full state preservation
#
# WHY: Teams polling and crons burn tokens and cause context resets.
# Maintenance mode silences everything so we can focus on fixing
# root causes without the noise constantly overriding our work.
#
# Usage:
#   ./maintenance-mode.sh enter    # Save state, stop everything
#   ./maintenance-mode.sh exit     # Restore exact pre-maintenance state
#   ./maintenance-mode.sh status   # Show current state
#
# State is saved to ~/.openclaw/maintenance-state/ so it survives session resets.

set -euo pipefail

STATE_DIR="$HOME/.openclaw/maintenance-state"
FLAG_FILE="$HOME/.openclaw/workspace/MAINTENANCE_MODE.md"
CRONTAB_BACKUP="$STATE_DIR/crontab.bak"
SERVICES_BACKUP="$STATE_DIR/systemd-services.json"
CRONS_BACKUP="$STATE_DIR/openclaw-crons.json"
HEARTBEAT_BACKUP="$STATE_DIR/heartbeat.json"

log() { echo "[maintenance] $(date '+%H:%M:%S') $*"; }

save_state() {
    mkdir -p "$STATE_DIR"
    log "Saving pre-maintenance state to $STATE_DIR"

    # 1. Linux crontab
    if crontab -l > "$CRONTAB_BACKUP" 2>/dev/null; then
        local lines=$(wc -l < "$CRONTAB_BACKUP")
        log "  Crontab saved ($lines lines)"
    else
        echo "# empty" > "$CRONTAB_BACKUP"
        log "  Crontab was empty"
    fi

    # 2. Systemd user services (teams-poller, webhook-server, openclaw-bridge, etc.)
    python3 -c "
import subprocess, json

services = ['teams-poller', 'webhook-server', 'openclaw-bridge', 'openclaw-gateway']
state = {}
for svc in services:
    svc_name = f'{svc}.service'
    try:
        active = subprocess.run(
            ['systemctl', '--user', 'is-active', svc_name],
            capture_output=True, text=True
        ).stdout.strip()
    except:
        active = 'unknown'
    try:
        enabled = subprocess.run(
            ['systemctl', '--user', 'is-enabled', svc_name],
            capture_output=True, text=True
        ).stdout.strip()
    except:
        enabled = 'unknown'
    state[svc] = {'active': active, 'enabled': enabled}
    
with open('$SERVICES_BACKUP', 'w') as f:
    json.dump(state, f, indent=2)
print(json.dumps(state, indent=2))
"
    log "  Systemd services saved"

    # 3. OpenClaw crons
    python3 -c "
import subprocess, json, sys

result = subprocess.run(
    ['openclaw', 'cron', 'list', '--json'],
    capture_output=True, text=True
)

# Try JSON parse, fall back to line parsing
crons = []
try:
    data = json.loads(result.stdout)
    if isinstance(data, list):
        crons = data
    elif isinstance(data, dict) and 'crons' in data:
        crons = data['crons']
except json.JSONDecodeError:
    # Parse the table output instead
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if parts and len(parts[0]) == 36 and '-' in parts[0]:  # UUID
            crons.append({
                'id': parts[0],
                'name': parts[1] if len(parts) > 1 else 'unknown',
                'enabled': True  # if it shows in list, it was enabled
            })

# Save whatever we got
with open('$CRONS_BACKUP', 'w') as f:
    json.dump(crons, f, indent=2)
print(f'Saved {len(crons)} cron entries')
" 2>/dev/null || log "  Warning: could not parse openclaw crons (may already be disabled)"

    # Also save the raw cron list output for reference
    openclaw cron list > "$STATE_DIR/openclaw-crons-raw.txt" 2>/dev/null || true
    log "  OpenClaw crons saved"

    # 4. Record timestamp
    echo "$(date -Iseconds)" > "$STATE_DIR/entered-at.txt"
    log "  State snapshot complete"
}

stop_everything() {
    log "Stopping all polling and crons..."

    # 1. Stop systemd services (except gateway — we need that for Slack DM)
    for svc in teams-poller webhook-server openclaw-bridge; do
        if systemctl --user is-active "$svc.service" &>/dev/null; then
            systemctl --user stop "$svc.service"
            log "  Stopped $svc"
        else
            log "  $svc already stopped"
        fi
    done

    # 2. Disable OpenClaw crons
    local cron_ids=$(openclaw cron list 2>/dev/null | awk 'NR>1 && /^[a-f0-9-]{36}/ {print $1}')
    if [ -n "$cron_ids" ]; then
        for id in $cron_ids; do
            openclaw cron disable "$id" 2>/dev/null && log "  Disabled cron $id" || true
        done
    else
        log "  No active OpenClaw crons to disable"
    fi

    # 3. Clear Linux crontab
    echo "# MAINTENANCE MODE - entered $(date)" | crontab -
    log "  Crontab cleared"

    # 4. Write flag file
    cat > "$FLAG_FILE" << 'FLAGEOF'
# 🔧 MAINTENANCE MODE — ACTIVE

All external polling, crons, and I/O are paused.
Only Slack DM with Joel is active.

**Why:** Stop token burn from polling so we can fix root causes.

**To exit:** Run `bash scripts/maintenance-mode.sh exit` or tell Coconut to exit maintenance mode.

**State preserved in:** `~/.openclaw/maintenance-state/`
FLAGEOF
    log "  Flag file written"

    log "=== MAINTENANCE MODE ACTIVE ==="
}

restore_state() {
    if [ ! -d "$STATE_DIR" ]; then
        log "ERROR: No saved state found at $STATE_DIR"
        exit 1
    fi

    log "Restoring pre-maintenance state from $STATE_DIR"
    local entered=$(cat "$STATE_DIR/entered-at.txt" 2>/dev/null || echo "unknown")
    log "  Maintenance was entered at: $entered"

    # 1. Restore Linux crontab
    if [ -f "$CRONTAB_BACKUP" ] && [ "$(cat "$CRONTAB_BACKUP")" != "# empty" ]; then
        crontab "$CRONTAB_BACKUP"
        local lines=$(crontab -l | wc -l)
        log "  Crontab restored ($lines lines)"
    else
        log "  Crontab backup was empty, skipping"
    fi

    # 2. Restore systemd services
    if [ -f "$SERVICES_BACKUP" ]; then
        python3 -c "
import subprocess, json

with open('$SERVICES_BACKUP') as f:
    state = json.load(f)

for svc, info in state.items():
    svc_name = f'{svc}.service'
    # Skip gateway — should always be running
    if svc == 'openclaw-gateway':
        continue
    
    if info.get('enabled') == 'enabled':
        subprocess.run(['systemctl', '--user', 'enable', svc_name], 
                       capture_output=True)
        print(f'  Enabled {svc}')
    
    if info.get('active') == 'active':
        subprocess.run(['systemctl', '--user', 'start', svc_name],
                       capture_output=True)
        print(f'  Started {svc}')
    else:
        print(f'  {svc} was {info.get(\"active\", \"unknown\")} before — not starting')
"
        log "  Systemd services restored"
    fi

    # 3. Re-enable OpenClaw crons
    if [ -f "$CRONS_BACKUP" ]; then
        python3 -c "
import subprocess, json

with open('$CRONS_BACKUP') as f:
    crons = json.load(f)

for cron in crons:
    cron_id = cron.get('id', '')
    if cron_id:
        result = subprocess.run(
            ['openclaw', 'cron', 'enable', cron_id],
            capture_output=True, text=True
        )
        name = cron.get('name', cron_id[:12])
        if result.returncode == 0:
            print(f'  Enabled cron: {name}')
        else:
            print(f'  Failed to enable cron: {name} ({result.stderr.strip()})')
" 2>/dev/null
        log "  OpenClaw crons restored"
    fi

    # 4. Remove flag file
    rm -f "$FLAG_FILE"
    log "  Flag file removed"

    # 5. Keep state dir as archive (don't delete — never delete, always archive)
    mv "$STATE_DIR" "$STATE_DIR.last-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true

    log "=== MAINTENANCE MODE EXITED ==="
}

show_status() {
    if [ -f "$FLAG_FILE" ]; then
        echo "MAINTENANCE MODE: ACTIVE"
        if [ -f "$STATE_DIR/entered-at.txt" ]; then
            echo "  Entered: $(cat "$STATE_DIR/entered-at.txt")"
        fi
        echo ""
        echo "Saved state:"
        [ -f "$CRONTAB_BACKUP" ] && echo "  Crontab: $(wc -l < "$CRONTAB_BACKUP") lines backed up"
        [ -f "$SERVICES_BACKUP" ] && echo "  Services: $(python3 -c "import json; print(json.dumps(json.load(open('$SERVICES_BACKUP'))))" 2>/dev/null)"
        [ -f "$CRONS_BACKUP" ] && echo "  Crons: $(python3 -c "import json; d=json.load(open('$CRONS_BACKUP')); print(f'{len(d)} entries')" 2>/dev/null)"
    else
        echo "MAINTENANCE MODE: INACTIVE"
    fi
}

case "${1:-status}" in
    enter)  save_state && stop_everything ;;
    exit)   restore_state ;;
    status) show_status ;;
    *)      echo "Usage: $0 {enter|exit|status}"; exit 1 ;;
esac
