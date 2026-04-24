#!/bin/bash
# Maintenance Mode — Enter/Exit with full state preservation
#
# WHY: Background polling burns tokens and causes context resets.
# This breaks the cycle: poll → tokens → compaction → lose progress → restart.
#
# DESIGN: Auto-discovers noise sources by pattern, not hardcoded names.
# Works on any OpenClaw environment regardless of custom services.
#
# Usage:
#   maintenance-mode.sh enter    # Discover + save state + stop everything
#   maintenance-mode.sh exit     # Restore exact pre-maintenance state
#   maintenance-mode.sh status   # Show current state

set -euo pipefail

STATE_DIR="$HOME/.openclaw/maintenance-state"
# Flag file in workspace root (find it dynamically)
WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
FLAG_FILE="$WORKSPACE/MAINTENANCE_MODE.md"
CRONTAB_BACKUP="$STATE_DIR/crontab.bak"
SERVICES_BACKUP="$STATE_DIR/systemd-services.json"
CRONS_BACKUP="$STATE_DIR/openclaw-crons.json"
NETWORK_SCAN="$STATE_DIR/network-scan.txt"

log() { echo "[maintenance] $(date '+%H:%M:%S') $*"; }

# ── Discovery ────────────────────────────────────────────────────

# Patterns that indicate polling/monitoring services (case-insensitive)
SVC_PATTERNS="poll|monitor|bridge|sync|watch|webhook|cron|schedule|timer|fetch|scrape|poller"
# Services to NEVER stop (keep OpenClaw gateway alive for DM channel)
SVC_EXCLUDE="openclaw-gateway|openclaw-node"

discover_services() {
    # Find all user systemd services matching polling patterns, excluding gateway
    systemctl --user list-units --type=service --state=active --no-pager --plain 2>/dev/null \
        | awk '{print $1}' \
        | grep -iE "$SVC_PATTERNS" \
        | grep -viE "$SVC_EXCLUDE" \
        | sed 's/\.service$//' \
        || true
}

discover_network_pollers() {
    # Snapshot outbound connections that look like polling (repeated HTTP/API calls)
    # This is informational — we don't kill these automatically
    {
        echo "# Network connections at $(date)"
        echo "# Processes with active outbound HTTP/HTTPS connections:"
        ss -tnp 2>/dev/null | grep -E ':80 |:443 |:8080 |:8443 |:8445 ' | head -30 || true
        echo ""
        echo "# Recurring curl/python/node processes:"
        ps aux 2>/dev/null | grep -iE 'poll|fetch|sync|monitor|watch' | grep -v grep | head -20 || true
    }
}

# ── State Management ─────────────────────────────────────────────

save_state() {
    mkdir -p "$STATE_DIR"
    log "Saving pre-maintenance state to $STATE_DIR"

    # 1. Linux crontab
    if crontab -l > "$CRONTAB_BACKUP" 2>/dev/null; then
        local lines
        lines=$(wc -l < "$CRONTAB_BACKUP")
        log "  Crontab saved ($lines lines)"
    else
        echo "# empty" > "$CRONTAB_BACKUP"
        log "  Crontab was empty"
    fi

    # 2. Systemd user services — discover and record state
    local services
    services=$(discover_services)

    python3 - "$SERVICES_BACKUP" "$services" << 'PYEOF'
import subprocess, json, sys

backup_path = sys.argv[1]
service_names = [s for s in sys.argv[2].split('\n') if s.strip()]

# Also find ALL active user services for completeness
try:
    result = subprocess.run(
        ['systemctl', '--user', 'list-units', '--type=service', '--state=active',
         '--no-pager', '--plain'],
        capture_output=True, text=True, timeout=10
    )
    all_active = set()
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if parts:
            all_active.add(parts[0].replace('.service', ''))
except Exception:
    all_active = set()

state = {}
for svc in service_names:
    svc_name = f'{svc}.service'
    try:
        active = subprocess.run(
            ['systemctl', '--user', 'is-active', svc_name],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        active = 'unknown'
    try:
        enabled = subprocess.run(
            ['systemctl', '--user', 'is-enabled', svc_name],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        enabled = 'unknown'
    state[svc] = {'active': active, 'enabled': enabled, 'matched_pattern': True}

with open(backup_path, 'w') as f:
    json.dump(state, f, indent=2)

for svc, info in state.items():
    print(f"  Found: {svc} (active={info['active']}, enabled={info['enabled']})")
PYEOF
    log "  Systemd services discovered and saved"

    # 3. OpenClaw crons
    if command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

backup_path = sys.argv[1]
result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True, timeout=15)

crons = []
for line in result.stdout.strip().splitlines():
    parts = line.split()
    # Look for UUID-style IDs (36 chars with dashes)
    if parts and len(parts[0]) >= 36 and parts[0].count('-') == 4:
        cron_entry = {'id': parts[0]}
        if len(parts) > 1:
            cron_entry['name'] = parts[1]
        # Check if status column says ok/error/idle (meaning enabled)
        line_lower = line.lower()
        cron_entry['was_enabled'] = 'disabled' not in line_lower
        crons.append(cron_entry)

with open(backup_path, 'w') as f:
    json.dump(crons, f, indent=2)
print(f"  Saved {len(crons)} OpenClaw cron entries")
PYEOF
    else
        echo "[]" > "$CRONS_BACKUP"
        log "  openclaw not found, skipping cron backup"
    fi

    # 4. Network scan (informational)
    discover_network_pollers > "$NETWORK_SCAN"
    log "  Network snapshot saved"

    # 5. Timestamp
    date -Iseconds > "$STATE_DIR/entered-at.txt"
    log "  State snapshot complete"
}

stop_everything() {
    log "Stopping all discovered noise sources..."

    # 1. Stop discovered systemd services
    if [ -f "$SERVICES_BACKUP" ]; then
        python3 - "$SERVICES_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    state = json.load(f)

for svc, info in state.items():
    svc_name = f'{svc}.service'
    if info.get('active') == 'active':
        result = subprocess.run(
            ['systemctl', '--user', 'stop', svc_name],
            capture_output=True, text=True, timeout=10
        )
        status = 'stopped' if result.returncode == 0 else f'failed: {result.stderr.strip()}'
        print(f"  {svc}: {status}")
    else:
        print(f"  {svc}: already inactive")
PYEOF
    fi

    # 2. Disable OpenClaw crons
    if [ -f "$CRONS_BACKUP" ] && command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    crons = json.load(f)

disabled = 0
for cron in crons:
    cron_id = cron.get('id', '')
    if cron_id and cron.get('was_enabled', True):
        result = subprocess.run(
            ['openclaw', 'cron', 'disable', cron_id],
            capture_output=True, text=True, timeout=10
        )
        name = cron.get('name', cron_id[:12])
        if result.returncode == 0:
            disabled += 1
        print(f"  Disabled cron: {name}")

print(f"  Total disabled: {disabled}/{len(crons)}")
PYEOF
    fi

    # 3. Clear Linux crontab
    echo "# MAINTENANCE MODE - entered $(date)" | crontab -
    log "  Crontab cleared"

    # 4. Write flag file
    cat > "$FLAG_FILE" << FLAGEOF
# 🔧 MAINTENANCE MODE — ACTIVE

All external polling, crons, and services are paused.
State preserved in \`~/.openclaw/maintenance-state/\` for instant restore.

**Entered:** $(date)
**Why:** Stop token burn from background polling so we can fix root causes.

**To exit:** \`bash scripts/maintenance-mode.sh exit\` or tell your agent to exit maintenance mode.
FLAGEOF
    log "  Flag file written"

    log "=== MAINTENANCE MODE ACTIVE ==="
}

restore_state() {
    if [ ! -d "$STATE_DIR" ]; then
        log "ERROR: No saved state at $STATE_DIR — was maintenance mode entered?"
        exit 1
    fi

    log "Restoring pre-maintenance state..."
    [ -f "$STATE_DIR/entered-at.txt" ] && log "  Was entered at: $(cat "$STATE_DIR/entered-at.txt")"

    # 1. Restore Linux crontab
    if [ -f "$CRONTAB_BACKUP" ] && [ "$(cat "$CRONTAB_BACKUP")" != "# empty" ]; then
        crontab "$CRONTAB_BACKUP"
        local lines
        lines=$(crontab -l 2>/dev/null | wc -l)
        log "  Crontab restored ($lines lines)"
    else
        log "  Crontab was empty before, clearing"
        crontab -r 2>/dev/null || true
    fi

    # 2. Restore systemd services to exact prior state
    if [ -f "$SERVICES_BACKUP" ]; then
        python3 - "$SERVICES_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    state = json.load(f)

for svc, info in state.items():
    svc_name = f'{svc}.service'

    if info.get('enabled') == 'enabled':
        subprocess.run(['systemctl', '--user', 'enable', svc_name],
                       capture_output=True, timeout=10)

    if info.get('active') == 'active':
        result = subprocess.run(['systemctl', '--user', 'start', svc_name],
                       capture_output=True, text=True, timeout=10)
        status = 'started' if result.returncode == 0 else f'failed: {result.stderr.strip()}'
        print(f"  {svc}: {status}")
    else:
        print(f"  {svc}: was {info.get('active', 'unknown')} — not starting")
PYEOF
        log "  Systemd services restored"
    fi

    # 3. Re-enable OpenClaw crons
    if [ -f "$CRONS_BACKUP" ] && command -v openclaw &>/dev/null; then
        python3 - "$CRONS_BACKUP" << 'PYEOF'
import subprocess, json, sys

with open(sys.argv[1]) as f:
    crons = json.load(f)

enabled = 0
for cron in crons:
    cron_id = cron.get('id', '')
    if cron_id and cron.get('was_enabled', True):
        result = subprocess.run(
            ['openclaw', 'cron', 'enable', cron_id],
            capture_output=True, text=True, timeout=10
        )
        name = cron.get('name', cron_id[:12])
        if result.returncode == 0:
            enabled += 1
        print(f"  Enabled cron: {name}")

print(f"  Total enabled: {enabled}/{len(crons)}")
PYEOF
        log "  OpenClaw crons restored"
    fi

    # 4. Remove flag file
    rm -f "$FLAG_FILE"
    log "  Flag file removed"

    # 5. Archive state (never delete)
    local archive="$STATE_DIR.last-$(date +%Y%m%d-%H%M%S)"
    mv "$STATE_DIR" "$archive" 2>/dev/null || true
    log "  State archived to $(basename "$archive")"

    log "=== MAINTENANCE MODE EXITED ==="
}

show_status() {
    if [ -f "$FLAG_FILE" ]; then
        echo "MAINTENANCE MODE: ACTIVE"
        [ -f "$STATE_DIR/entered-at.txt" ] && echo "  Entered: $(cat "$STATE_DIR/entered-at.txt")"
        echo ""
        echo "Saved state in $STATE_DIR:"
        [ -f "$CRONTAB_BACKUP" ] && echo "  Crontab: $(wc -l < "$CRONTAB_BACKUP") lines backed up"
        [ -f "$SERVICES_BACKUP" ] && echo "  Services: $(python3 -c "import json; d=json.load(open('$SERVICES_BACKUP')); print(', '.join(f'{k}={v[\"active\"]}' for k,v in d.items()))" 2>/dev/null || echo "saved")"
        [ -f "$CRONS_BACKUP" ] && echo "  Crons: $(python3 -c "import json; print(f'{len(json.load(open(\"$CRONS_BACKUP\")))} entries')" 2>/dev/null || echo "saved")"
        [ -f "$NETWORK_SCAN" ] && echo "  Network: snapshot saved"
    else
        echo "MAINTENANCE MODE: INACTIVE"
        # Check if archived states exist
        local archives
        archives=$(ls -d "$STATE_DIR".last-* 2>/dev/null | wc -l)
        [ "$archives" -gt 0 ] && echo "  Previous sessions: $archives archived"
    fi
}

case "${1:-status}" in
    enter)  save_state && stop_everything ;;
    exit)   restore_state ;;
    status) show_status ;;
    *)      echo "Usage: $0 {enter|exit|status}"; exit 1 ;;
esac
