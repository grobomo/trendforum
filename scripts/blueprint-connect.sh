#!/bin/bash
# blueprint-connect.sh — Connect Blueprint MCP to Windows Chrome extension
# 
# Blueprint MCP (WSL) <-> Chrome Extension (Windows) communication:
# - Chrome extension runs a WebSocket relay on Windows localhost
# - WSL2 can reach Windows host via the WSL gateway IP or localhost
# - This script ensures connectivity and starts the MCP server
#
# Usage: ./blueprint-connect.sh [--check|--start|--relay]

set -euo pipefail

BLUEPRINT_DIR="/mnt/c/Users/joelg/Documents/ProjectsCL1/_shared/MCP/blueprint-extra-mcp"
BLUEPRINT_PORT="${BLUEPRINT_PORT:-5555}"
WIN_HOST=$(ip route show default | awk '{print $3}')  # WSL2 gateway = Windows host

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Check if Chrome extension relay is reachable
check_relay() {
    log "Checking Blueprint relay on Windows host..."
    log "  Windows host IP: $WIN_HOST"
    log "  Relay port: $BLUEPRINT_PORT"
    
    # Try localhost first (WSL2 localhost forwarding)
    if curl -sf --connect-timeout 3 "http://127.0.0.1:$BLUEPRINT_PORT/" >/dev/null 2>&1; then
        log "  ✅ Relay reachable via localhost:$BLUEPRINT_PORT"
        return 0
    fi
    
    # Try Windows host IP
    if curl -sf --connect-timeout 3 "http://$WIN_HOST:$BLUEPRINT_PORT/" >/dev/null 2>&1; then
        log "  ✅ Relay reachable via $WIN_HOST:$BLUEPRINT_PORT"
        return 0
    fi
    
    # WebSocket check (relay might not respond to HTTP)
    # Try a quick TCP connect
    if timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/$BLUEPRINT_PORT" 2>/dev/null; then
        log "  ✅ TCP connection to localhost:$BLUEPRINT_PORT succeeded (WebSocket expected)"
        return 0
    fi
    
    if timeout 3 bash -c "echo >/dev/tcp/$WIN_HOST/$BLUEPRINT_PORT" 2>/dev/null; then
        log "  ✅ TCP connection to $WIN_HOST:$BLUEPRINT_PORT succeeded (WebSocket expected)"
        return 0
    fi
    
    log "  ❌ Relay not reachable"
    log ""
    log "Troubleshooting:"
    log "  1. Is Chrome running with Blueprint extension enabled?"
    log "  2. Check extension popup — should show 'Connected' or 'Listening'"
    log "  3. Try disabling/re-enabling the extension"
    log "  4. Windows Firewall may block port $BLUEPRINT_PORT from WSL"
    return 1
}

# Set up socat relay if direct connection fails (creative network relay)
setup_relay() {
    log "Setting up socat relay: WSL localhost:$BLUEPRINT_PORT -> Windows $WIN_HOST:$BLUEPRINT_PORT"
    
    if ! command -v socat >/dev/null 2>&1; then
        log "Installing socat..."
        sudo apt-get install -y -qq socat 2>/dev/null
    fi
    
    # Kill any existing relay
    pkill -f "socat.*:$BLUEPRINT_PORT" 2>/dev/null || true
    sleep 1
    
    # Create TCP relay
    socat TCP-LISTEN:$BLUEPRINT_PORT,reuseaddr,fork TCP:$WIN_HOST:$BLUEPRINT_PORT &
    RELAY_PID=$!
    log "  Relay PID: $RELAY_PID"
    
    sleep 1
    if kill -0 $RELAY_PID 2>/dev/null; then
        log "  ✅ Relay running"
        echo $RELAY_PID > /tmp/blueprint-relay.pid
    else
        log "  ❌ Relay failed to start"
        return 1
    fi
}

# Alternative: use Windows netsh portproxy for persistent forwarding
setup_windows_portproxy() {
    log "Setting up Windows netsh portproxy (requires admin)..."
    local wsl_ip
    wsl_ip=$(hostname -I | awk '{print $1}')
    
    # This runs on Windows side
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -Command "
        Start-Process netsh -ArgumentList 'interface portproxy add v4tov4 listenport=$BLUEPRINT_PORT listenaddress=0.0.0.0 connectport=$BLUEPRINT_PORT connectaddress=$wsl_ip' -Verb RunAs
    " 2>&1
    
    log "  Port proxy configured: Windows *:$BLUEPRINT_PORT -> WSL $wsl_ip:$BLUEPRINT_PORT"
}

# Start Blueprint MCP via mcpm
start_mcp() {
    log "Starting Blueprint MCP via mcp-manager..."
    
    # Check if already running
    if openclaw mcp status blueprint-extra 2>/dev/null | grep -q "running"; then
        log "  Already running"
        return 0
    fi
    
    # Start it
    openclaw mcp start blueprint-extra 2>&1
    log "  ✅ Blueprint MCP started"
}

# Full connection sequence
connect() {
    log "=== Blueprint MCP -> Windows Chrome Connection ==="
    log ""
    
    # Step 1: Check if relay is reachable
    if ! check_relay; then
        log ""
        log "Direct connection failed. Attempting socat relay..."
        setup_relay
        
        if ! check_relay; then
            log ""
            log "❌ Cannot reach Chrome extension. Make sure:"
            log "   - Chrome is running on Windows"
            log "   - Blueprint MCP extension is installed and enabled"
            log "   - Extension shows 'Listening' state"
            return 1
        fi
    fi
    
    log ""
    log "=== Connection ready ==="
    log "Blueprint MCP can reach Chrome extension at port $BLUEPRINT_PORT"
    log ""
    log "Next: Use mcp-manager to call blueprint-extra tools:"
    log "  mcpm call blueprint-extra enable"
    log "  mcpm call blueprint-extra browser_tabs '{\"action\":\"list\"}'"
}

# Main
case "${1:---start}" in
    --check)  check_relay ;;
    --start)  connect ;;
    --relay)  setup_relay ;;
    --proxy)  setup_windows_portproxy ;;
    *)        echo "Usage: $0 [--check|--start|--relay|--proxy]"; exit 1 ;;
esac
