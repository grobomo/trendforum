#!/bin/bash
# deploy-guardrails.sh — Deploy coconut-guardrails from source repo to extensions
#
# Source: ~/.openclaw/plugins/coconut-guardrails/ (git repo)
# Target: ~/.openclaw/extensions/coconut-guardrails/ (gateway runtime)
#
# Steps:
# 1. Backup current extensions copy
# 2. Sync source → extensions
# 3. Restart gateway
# 4. Health check
# 5. Rollback if unhealthy

set -euo pipefail

SOURCE="$HOME/.openclaw/plugins/coconut-guardrails"
TARGET="$HOME/.openclaw/extensions/coconut-guardrails"
BACKUP_DIR="$HOME/.openclaw/backups/extensions/coconut-guardrails"
TIMESTAMP=$(date -u +%Y-%m-%dT%H-%M-%SZ)

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

# 1. Backup current extensions copy
log "Backing up current extensions..."
mkdir -p "$BACKUP_DIR/$TIMESTAMP"
cp "$TARGET"/*.ts "$TARGET"/*.json "$BACKUP_DIR/$TIMESTAMP/" 2>/dev/null || true
log "Backup: $BACKUP_DIR/$TIMESTAMP/"

# 2. Sync source → extensions (only .ts, .json, .js files)
log "Syncing $SOURCE → $TARGET..."
for ext in ts json js; do
    for f in "$SOURCE"/*.$ext; do
        [ -f "$f" ] && cp "$f" "$TARGET/"
    done
done
log "Sync complete"

# 3. Restart gateway
log "Restarting gateway..."
openclaw gateway restart 2>&1 || true
sleep 3

# 4. Health check
log "Health check..."
if openclaw health --json --timeout 10000 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status') in ('ok','healthy') else 1)" 2>/dev/null; then
    log "✅ Gateway healthy after deploy"
    exit 0
fi

# 5. Rollback
log "❌ Gateway unhealthy — rolling back..."
for f in "$BACKUP_DIR/$TIMESTAMP"/*; do
    [ -f "$f" ] && cp "$f" "$TARGET/"
done
openclaw gateway restart 2>&1 || true
sleep 3

if openclaw health --json --timeout 10000 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status') in ('ok','healthy') else 1)" 2>/dev/null; then
    log "✅ Rollback successful"
    exit 1
else
    log "❌ Rollback failed — gateway still unhealthy. Manual intervention needed."
    exit 2
fi
