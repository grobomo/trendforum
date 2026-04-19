#!/bin/bash
# Recording Analyzer File Watcher
# Polls for new .vtt files in the transcripts directory and triggers analysis
# Uses polling since inotify doesn't work on /mnt/c/ (Windows filesystem)

TRANSCRIPTS_DIR="/mnt/c/Users/joelg/Documents/ProjectsCL1/_tmemu/recording-analyzer/transcripts"
PROJECT_DIR="/mnt/c/Users/joelg/Documents/ProjectsCL1/_tmemu/recording-analyzer"
STATE_FILE="/home/ubu/.openclaw/workspace/memory/recording-watcher-state.json"
LOG_FILE="/home/ubu/.openclaw/workspace/logs/recording-watcher.log"
POLL_INTERVAL=300  # 5 minutes

mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $1" >> "$LOG_FILE"
}

# Initialize state file if missing
if [ ! -f "$STATE_FILE" ]; then
    echo '{"known_files": [], "last_check": null}' > "$STATE_FILE"
fi

log "Recording watcher started (poll every ${POLL_INTERVAL}s)"

while true; do
    # Get current .vtt files
    CURRENT_FILES=$(find "$TRANSCRIPTS_DIR" -maxdepth 1 -name "*.vtt" -printf "%f\n" 2>/dev/null | sort)
    
    # Get known files from state
    KNOWN_FILES=$(python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)
for f in sorted(state.get('known_files', [])):
    print(f)
" 2>/dev/null)
    
    # Find new files
    NEW_FILES=$(comm -23 <(echo "$CURRENT_FILES") <(echo "$KNOWN_FILES"))
    
    if [ -n "$NEW_FILES" ]; then
        log "New VTT files detected:"
        echo "$NEW_FILES" | while read -r vtt; do
            log "  → $vtt"
            
            # Notify via OpenClaw system event
            openclaw system event --text "New recording transcript detected: $vtt — run recording-analyzer import + analysis" --mode now 2>/dev/null || true
        done
        
        # Update state
        python3 -c "
import json, datetime
with open('$STATE_FILE') as f:
    state = json.load(f)
current = set(state.get('known_files', []))
$(echo "$CURRENT_FILES" | while read -r f; do echo "current.add('$f')"; done)
state['known_files'] = sorted(current)
state['last_check'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null
    else
        # Update last_check timestamp only
        python3 -c "
import json, datetime
with open('$STATE_FILE') as f:
    state = json.load(f)
state['last_check'] = datetime.datetime.utcnow().isoformat() + 'Z'
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null
    fi
    
    sleep "$POLL_INTERVAL"
done
