#!/usr/bin/env bash
#
# OpenClaw Personal Assistant — Setup Script
# ============================================
# Deploys a full OpenClaw assistant instance for Trend Micro squad members.
# Supports macOS, Linux, and Windows WSL2.
#
# What you get:
#   - OpenClaw Gateway (systemd/launchd service)
#   - Slack channel integration
#   - RDsec AI Endpoint (Claude models via Trend internal API)
#   - Linux keyring for secrets
#   - Optional: Claude Code CLI for coding tasks
#
# Usage:
#   bash deploy-openclaw.sh
#
# Prerequisites:
#   - Node.js 22+ (installed or we install via nvm)
#   - Git
#   - An RDsec API key (provided by Joel)
#   - A Slack app (bot token + app token — see docs)
#
# Author: Coconut (Joel's AI assistant)
# Last updated: 2026-04-25
#

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Globals ─────────────────────────────────────────────────────────────────
OPENCLAW_HOME="$HOME/.openclaw"
OPENCLAW_VERSION="latest"
MIN_NODE_MAJOR=22
LOG_FILE="/tmp/openclaw-setup-$(date +%Y%m%d-%H%M%S).log"

# ── Helpers ─────────────────────────────────────────────────────────────────
log()  { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
info() { echo -e "  ${CYAN}→${NC} $*"; }
step() { echo ""; echo -e "${BOLD}$*${NC}"; }

die() {
    fail "$1"
    echo "  See full log: $LOG_FILE"
    exit 1
}

prompt_yn() {
    local msg="$1" default="${2:-y}"
    if [ "$default" = "y" ]; then
        read -rp "  $msg [Y/n] " ans
        [[ "$ans" =~ ^[Nn]$ ]] && return 1 || return 0
    else
        read -rp "  $msg [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && return 0 || return 1
    fi
}

prompt_val() {
    local msg="$1" var_name="$2" default="${3:-}"
    if [ -n "$default" ]; then
        read -rp "  $msg [$default]: " val
        eval "$var_name='${val:-$default}'"
    else
        read -rp "  $msg: " val
        eval "$var_name='$val'"
    fi
}

# ── Detect OS ───────────────────────────────────────────────────────────────
detect_os() {
    OS="unknown"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -qi microsoft /proc/version 2>/dev/null; then
            OS="wsl"
        else
            OS="linux"
        fi
    fi
    echo "$OS"
}

# ── Banner ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}🌴 OpenClaw Personal Assistant — Setup Script${NC}"
echo "═══════════════════════════════════════════════════"
echo ""
echo "This script will set up your own AI assistant instance."
echo "It runs as a background service and connects to Slack."
echo ""
echo "Log file: $LOG_FILE"
echo ""

OS=$(detect_os)
log "Detected OS: $OS"

if [ "$OS" = "unknown" ]; then
    die "Unsupported OS. This script supports macOS, Linux, and WSL2."
fi

# ── Step 1: Node.js ────────────────────────────────────────────────────────
step "Step 1/8: Node.js"

install_nvm_and_node() {
    info "Installing nvm..."
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash >> "$LOG_FILE" 2>&1
    export NVM_DIR="$HOME/.nvm"
    # shellcheck disable=SC1091
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    info "Installing Node.js v22 (LTS)..."
    nvm install 22 >> "$LOG_FILE" 2>&1
    nvm use 22 >> "$LOG_FILE" 2>&1
    nvm alias default 22 >> "$LOG_FILE" 2>&1
    log "Node.js $(node -v) installed via nvm"
}

if command -v node &>/dev/null; then
    NODE_V=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_V" -ge "$MIN_NODE_MAJOR" ]; then
        log "Node.js $(node -v) — OK"
    else
        warn "Node.js $(node -v) is too old (need v${MIN_NODE_MAJOR}+)"
        if prompt_yn "Install Node.js 22 via nvm?"; then
            install_nvm_and_node
        else
            die "Node.js ${MIN_NODE_MAJOR}+ is required."
        fi
    fi
else
    warn "Node.js not found"
    if prompt_yn "Install Node.js 22 via nvm?"; then
        install_nvm_and_node
    else
        die "Node.js ${MIN_NODE_MAJOR}+ is required."
    fi
fi

# ── Step 2: Git check ──────────────────────────────────────────────────────
step "Step 2/8: Git"
if command -v git &>/dev/null; then
    log "git $(git --version | awk '{print $3}') — OK"
else
    die "Git is required. Install with: sudo apt install git (Linux/WSL) or brew install git (Mac)"
fi

# ── Step 3: Install OpenClaw ───────────────────────────────────────────────
step "Step 3/8: OpenClaw"

if command -v openclaw &>/dev/null; then
    CURRENT_V=$(openclaw --version 2>/dev/null | head -1)
    log "OpenClaw already installed: $CURRENT_V"
    if prompt_yn "Update to latest?"; then
        info "Updating..."
        npm install -g openclaw >> "$LOG_FILE" 2>&1
        log "Updated to $(openclaw --version 2>/dev/null | head -1)"
    fi
else
    info "Installing OpenClaw globally..."
    npm install -g openclaw >> "$LOG_FILE" 2>&1 || die "npm install failed. Check $LOG_FILE"
    log "OpenClaw $(openclaw --version 2>/dev/null | head -1) installed"
fi

# ── Step 4: Secrets (Keyring) ──────────────────────────────────────────────
step "Step 4/8: API Keys & Secrets"

# Ensure keyring dependencies
if [ "$OS" = "mac" ]; then
    # macOS uses native Keychain — no extra deps
    info "macOS Keychain — no extra packages needed"
elif [ "$OS" = "wsl" ] || [ "$OS" = "linux" ]; then
    # Need gnome-keyring + secret-tool + python3-keyring
    NEED_PKGS=()
    command -v secret-tool &>/dev/null || NEED_PKGS+=(libsecret-tools)
    python3 -c "import keyring" 2>/dev/null || NEED_PKGS+=(python3-keyring)
    dpkg -s gnome-keyring &>/dev/null 2>&1 || NEED_PKGS+=(gnome-keyring)

    if [ ${#NEED_PKGS[@]} -gt 0 ]; then
        warn "Need to install keyring packages: ${NEED_PKGS[*]}"
        if prompt_yn "Install now (requires sudo)?"; then
            sudo apt-get update -qq >> "$LOG_FILE" 2>&1
            sudo apt-get install -y -qq "${NEED_PKGS[@]}" >> "$LOG_FILE" 2>&1
            log "Keyring packages installed"
        else
            warn "Skipping — you'll need to set up secrets manually"
        fi
    else
        log "Keyring packages — OK"
    fi

    # Initialize keyring if on WSL/headless
    if [ ! -d "$HOME/.local/share/keyrings" ]; then
        info "Initializing gnome-keyring for headless use..."
        mkdir -p "$HOME/.local/share/keyrings"

        # Check if dbus session is running
        if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
            warn "No D-Bus session. You may need to run:"
            echo "    eval \$(dbus-launch --sh-syntax)"
            echo "  and add it to your ~/.bashrc"
        fi
    fi
fi

echo ""
echo "  You need the following API keys:"
echo "    1. RDsec API Key (required) — powers the LLM"
echo "    2. Slack Bot Token (optional) — for Slack channel"
echo "    3. Slack App Token (optional) — for Slack socket mode"
echo ""
echo "  Ask Joel for these if you don't have them."
echo ""

store_secret() {
    local name="$1" prompt_msg="$2" required="${3:-false}"
    local val=""

    # Check if already stored
    if command -v secret-tool &>/dev/null; then
        val=$(secret-tool lookup service openclaw username "$name" 2>/dev/null || true)
    elif [ "$OS" = "mac" ]; then
        val=$(security find-generic-password -s openclaw -a "$name" -w 2>/dev/null || true)
    fi

    if [ -n "$val" ]; then
        log "$name already stored in keyring"
        if ! prompt_yn "Update it?" "n"; then
            return 0
        fi
    fi

    read -rsp "  Enter $prompt_msg (or Enter to skip): " val
    echo ""
    if [ -z "$val" ]; then
        if [ "$required" = "true" ]; then
            warn "$name is required — you'll need to set it later"
            echo "    Run: secret-tool store --label='$name' service openclaw username $name"
        fi
        return 0
    fi

    if command -v secret-tool &>/dev/null; then
        echo -n "$val" | secret-tool store --label="$name on openclaw" service openclaw username "$name" 2>/dev/null
    elif [ "$OS" = "mac" ]; then
        security add-generic-password -s openclaw -a "$name" -w "$val" -U 2>/dev/null
    fi
    log "$name stored in keyring"
}

store_secret "RDSEC_API_KEY" "RDsec API Key" "true"
store_secret "SLACK_BOT_TOKEN" "Slack Bot Token" "false"
store_secret "SLACK_APP_TOKEN" "Slack App Token" "false"

# ── Step 5: Create load-secrets.py ─────────────────────────────────────────
step "Step 5/8: Secret Loader"

mkdir -p "$OPENCLAW_HOME"

cat > "$OPENCLAW_HOME/load-secrets.py" << 'PYEOF'
#!/usr/bin/env python3
"""Load secrets from keyring into a temporary env file for systemd."""
import keyring, os, sys, stat

required = {"RDSEC_API_KEY": ("openclaw", "RDSEC_API_KEY")}
optional = {
    "SLACK_BOT_TOKEN": ("openclaw", "SLACK_BOT_TOKEN"),
    "SLACK_APP_TOKEN": ("openclaw", "SLACK_APP_TOKEN"),
}
env_file = os.path.expanduser("~/.openclaw/.runtime-env")

lines = []
for env_var, (service, key) in required.items():
    val = keyring.get_password(service, key)
    if not val:
        print(f"FATAL: {service}/{key} not found in keyring", file=sys.stderr)
        sys.exit(1)
    lines.append(f"{env_var}={val}")
for env_var, (service, key) in optional.items():
    val = keyring.get_password(service, key)
    if val:
        lines.append(f"{env_var}={val}")

with open(env_file, "w") as f:
    f.write("\n".join(lines) + "\n")
os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)  # 600
print(f"Loaded {len(lines)} secrets from keyring")
PYEOF
chmod +x "$OPENCLAW_HOME/load-secrets.py"
log "Secret loader created"

# ── Step 6: OpenClaw Configuration ─────────────────────────────────────────
step "Step 6/8: OpenClaw Configuration"

ASSISTANT_NAME=""
prompt_val "What should your assistant be named?" ASSISTANT_NAME "assistant"

GATEWAY_PORT=""
prompt_val "Gateway port" GATEWAY_PORT "18789"

# Generate auth token
AUTH_TOKEN=$(openssl rand -hex 24 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(24))")

CONFIG_FILE="$OPENCLAW_HOME/openclaw.json"
if [ -f "$CONFIG_FILE" ]; then
    warn "Config file already exists at $CONFIG_FILE"
    if prompt_yn "Overwrite?"; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"
        info "Backed up existing config"
    else
        log "Keeping existing config"
        SKIP_CONFIG=true
    fi
fi

if [ "${SKIP_CONFIG:-}" != "true" ]; then
    NODE_PATH=$(which node)

    cat > "$CONFIG_FILE" << JSONEOF
{
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "port": ${GATEWAY_PORT},
    "auth": {
      "mode": "token",
      "token": "${AUTH_TOKEN}"
    },
    "http": {
      "endpoints": {
        "chatCompletions": { "enabled": true }
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "trendmicro-aiendpoint": {
        "baseUrl": "https://api.rdsec.trendmicro.com/prod/aiendpoint/v1",
        "apiKey": "\${RDSEC_API_KEY}",
        "api": "openai-completions",
        "authHeader": true,
        "models": [
          {
            "id": "claude-4.6-sonnet",
            "name": "Claude 4.6 Sonnet",
            "reasoning": true,
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 64000
          },
          {
            "id": "claude-4.6-opus",
            "name": "Claude 4.6 Opus",
            "reasoning": true,
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 128000
          },
          {
            "id": "claude-4.5-haiku",
            "name": "Claude 4.5 Haiku",
            "reasoning": false,
            "input": ["text", "image"],
            "contextWindow": 200000,
            "maxTokens": 64000
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "trendmicro-aiendpoint/claude-4.6-sonnet"
      },
      "timeoutSeconds": 300,
      "compaction": {
        "mode": "safeguard",
        "notifyUser": true
      }
    }
  },
  "channels": {
    "slack": {
      "enabled": true,
      "mode": "socket",
      "name": "${ASSISTANT_NAME}",
      "botToken": "\${SLACK_BOT_TOKEN}",
      "appToken": "\${SLACK_APP_TOKEN}",
      "dmPolicy": "allowlist",
      "allowFrom": [],
      "groupPolicy": "open",
      "capabilities": {
        "interactiveReplies": true
      },
      "thread": {
        "requireExplicitMention": true
      }
    }
  },
  "logging": {
    "level": "info"
  }
}
JSONEOF
    log "Config written to $CONFIG_FILE"
    info "Default model: Claude 4.6 Sonnet (cost-efficient)"
    info "Upgrade to Opus in config if you want maximum capability"
fi

# ── Step 7: Systemd Service ────────────────────────────────────────────────
step "Step 7/8: System Service"

if [ "$OS" = "mac" ]; then
    # macOS launchd
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.openclaw.gateway.plist"
    mkdir -p "$PLIST_DIR"

    NODE_PATH=$(which node)
    OPENCLAW_PATH=$(which openclaw)
    OPENCLAW_JS=$(readlink -f "$OPENCLAW_PATH" 2>/dev/null | sed 's|/bin/openclaw|/lib/node_modules/openclaw/dist/index.js|' || echo "")

    if [ -z "$OPENCLAW_JS" ] || [ ! -f "$OPENCLAW_JS" ]; then
        OPENCLAW_JS=$(npm root -g 2>/dev/null)/openclaw/dist/index.js
    fi

    cat > "$PLIST_FILE" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>${NODE_PATH}</string>
        <string>${OPENCLAW_JS}</string>
        <string>gateway</string>
        <string>--port</string>
        <string>${GATEWAY_PORT}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OPENCLAW_HOME}/logs/gateway.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${OPENCLAW_HOME}/logs/gateway.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>TMPDIR</key>
        <string>/tmp</string>
    </dict>
</dict>
</plist>
PLISTEOF
    mkdir -p "$OPENCLAW_HOME/logs"
    log "LaunchAgent plist created at $PLIST_FILE"

    if prompt_yn "Start the gateway service now?"; then
        launchctl load "$PLIST_FILE" 2>/dev/null || true
        sleep 2
        if launchctl list | grep -q com.openclaw.gateway; then
            log "Gateway service is running!"
        else
            warn "Service may not have started. Check: launchctl list | grep openclaw"
        fi
    fi

elif [ "$OS" = "wsl" ] || [ "$OS" = "linux" ]; then
    # systemd user service
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"

    NODE_PATH=$(which node)
    OPENCLAW_JS=$(dirname "$(readlink -f "$(which openclaw)" 2>/dev/null || which openclaw)")/../lib/node_modules/openclaw/dist/index.js

    # Resolve actual path
    if [ ! -f "$OPENCLAW_JS" ]; then
        OPENCLAW_JS=$(npm root -g 2>/dev/null)/openclaw/dist/index.js
    fi

    OC_VERSION=$(openclaw --version 2>/dev/null | head -1 || echo "unknown")

    cat > "$SYSTEMD_DIR/openclaw-gateway.service" << SVCEOF
[Unit]
Description=OpenClaw Gateway (v${OC_VERSION})
After=network-online.target
Wants=network-online.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
ExecStartPre=/usr/bin/python3 ${OPENCLAW_HOME}/load-secrets.py
ExecStart=${NODE_PATH} ${OPENCLAW_JS} gateway --port ${GATEWAY_PORT}
Restart=always
RestartSec=5
RestartPreventExitStatus=78
TimeoutStopSec=30
TimeoutStartSec=30
SuccessExitStatus=0 143
KillMode=control-group
EnvironmentFile=-${OPENCLAW_HOME}/.runtime-env
EnvironmentFile=-${OPENCLAW_HOME}/gateway.systemd.env
Environment=HOME=${HOME}
Environment=TMPDIR=/tmp
Environment=NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
Environment=PATH=${NODE_PATH%/node}:${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=OPENCLAW_GATEWAY_PORT=${GATEWAY_PORT}
Environment=OPENCLAW_SYSTEMD_UNIT=openclaw-gateway.service
Environment=OPENCLAW_SERVICE_MARKER=openclaw
Environment=OPENCLAW_SERVICE_KIND=gateway
Environment=OPENCLAW_SERVICE_VERSION=${OC_VERSION}
Environment=OPENCLAW_SERVICE_MANAGED_ENV_KEYS=RDSEC_API_KEY,SLACK_APP_TOKEN,SLACK_BOT_TOKEN
Environment=no_proxy=127.0.0.1,localhost,0.0.0.0
Environment=NO_PROXY=127.0.0.1,localhost,0.0.0.0

[Install]
WantedBy=default.target
SVCEOF

    log "Systemd service created"

    # Enable lingering for WSL (keeps user services running after logout)
    if [ "$OS" = "wsl" ]; then
        info "Enabling user linger (keeps service running when not logged in)..."
        sudo loginctl enable-linger "$USER" 2>/dev/null || warn "Could not enable linger — service may stop on logout"
    fi

    systemctl --user daemon-reload
    systemctl --user enable openclaw-gateway.service 2>/dev/null

    if prompt_yn "Start the gateway service now?"; then
        systemctl --user start openclaw-gateway.service
        sleep 3
        if systemctl --user is-active openclaw-gateway.service &>/dev/null; then
            log "Gateway service is running!"
            info "Check status: systemctl --user status openclaw-gateway"
        else
            warn "Service may not have started."
            info "Check logs: journalctl --user -u openclaw-gateway -f"
        fi
    fi
fi

# ── Step 8: Workspace ──────────────────────────────────────────────────────
step "Step 8/8: Workspace"

WORKSPACE_DIR="$OPENCLAW_HOME/workspace"
mkdir -p "$WORKSPACE_DIR"/{scripts,memory,specs,docs}

# Initialize MEMORY.md
if [ ! -f "$WORKSPACE_DIR/MEMORY.md" ]; then
    cat > "$WORKSPACE_DIR/MEMORY.md" << 'MDEOF'
# Memory

## Identity
- Assistant name: (set during setup)
- Operator: (your name)
- Team: Misfits Squad, Trend Micro

## Key Principles
- Act on tasks without asking for permission — just do it
- Be concise in responses
- Use memory files to maintain context across sessions
MDEOF
    log "Workspace initialized with starter MEMORY.md"
else
    log "Workspace already exists"
fi

# Initialize git in workspace
if [ ! -d "$WORKSPACE_DIR/.git" ]; then
    cd "$WORKSPACE_DIR"
    git init -q
    git add -A 2>/dev/null || true
    git commit -qm "Initial workspace setup" 2>/dev/null || true
    log "Workspace git repo initialized"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo -e "${BOLD}🌴 Setup Complete!${NC}"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Your assistant: ${ASSISTANT_NAME}"
echo "  Gateway port:   ${GATEWAY_PORT}"
echo "  Config file:    ${CONFIG_FILE}"
echo "  Workspace:      ${WORKSPACE_DIR}"
echo "  Logs:           journalctl --user -u openclaw-gateway -f"
echo ""
echo -e "${BOLD}Quick Commands:${NC}"
echo "  openclaw gateway status          # Check if gateway is running"
echo "  openclaw gateway restart         # Restart the gateway"
echo "  systemctl --user status openclaw-gateway  # Service status"
echo "  openclaw chat                    # Interactive chat in terminal"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo "  1. If you skipped API keys, add them now:"
echo "     secret-tool store --label='RDSEC_API_KEY' service openclaw username RDSEC_API_KEY"
echo "  2. Configure your Slack app (ask Joel for the Slack manifest)"
echo "  3. Add your Slack user ID to channels.slack.allowFrom in:"
echo "     ${CONFIG_FILE}"
echo "  4. Restart: systemctl --user restart openclaw-gateway"
echo ""
echo -e "${BOLD}Optional: Claude Code CLI${NC}"
echo "  npm install -g @anthropic-ai/claude-code"
echo "  export ANTHROPIC_API_KEY=\$(secret-tool lookup service openclaw username RDSEC_API_KEY)"
echo "  export ANTHROPIC_BASE_URL='https://api.rdsec.trendmicro.com/prod/aiendpoint/v1'"
echo ""
echo "Questions? Ask Joel or message Coconut in Slack (#coco-chat)"
echo "═══════════════════════════════════════════════════"
