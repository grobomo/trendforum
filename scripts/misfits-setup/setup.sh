#!/bin/bash
#
# Misfits Squad AI Tooling Setup Script
# =======================================
# Sets up Claude Code + MCP servers for Trend Micro squad members.
# Run this on your local machine (Mac or Windows WSL).
#
# Usage: bash setup.sh
#

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}🌴 Misfits AI Tooling Setup${NC}"
echo "============================================"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
    echo -e "${GREEN}✓${NC} Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if grep -qi microsoft /proc/version 2>/dev/null; then
        OS="wsl"
        echo -e "${GREEN}✓${NC} Detected: Windows (WSL)"
    else
        OS="linux"
        echo -e "${GREEN}✓${NC} Detected: Linux"
    fi
fi

# Step 1: Check prerequisites
echo ""
echo -e "${BOLD}Step 1: Checking prerequisites...${NC}"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found: $(command -v "$1")"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

MISSING=()
check_cmd node || MISSING+=(node)
check_cmd npm || MISSING+=(npm)
check_cmd git || MISSING+=(git)
check_cmd python3 || MISSING+=(python3)

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Missing required tools: ${MISSING[*]}${NC}"
    echo ""
    if [ "$OS" == "mac" ]; then
        echo "Install with Homebrew:"
        echo "  brew install node git python3"
    elif [ "$OS" == "wsl" ]; then
        echo "Install in WSL:"
        echo "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
        echo "  sudo apt install -y nodejs git python3 python3-pip"
    fi
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Step 2: Claude Code
echo ""
echo -e "${BOLD}Step 2: Claude Code${NC}"

if command -v claude &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Claude Code already installed"
    claude --version 2>/dev/null || true
else
    echo "  Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code 2>/dev/null || {
        echo -e "  ${YELLOW}⚠${NC} Install failed. Try: sudo npm install -g @anthropic-ai/claude-code"
    }
fi

# Step 3: RDsec API Key
echo ""
echo -e "${BOLD}Step 3: API Configuration${NC}"
echo ""
echo "You need an RDsec AI Endpoint API key."
echo "  → Request from: Joel Ginsberg or your manager"
echo "  → Portal: https://rdsec-aiendpoint.trendmicro.com"
echo ""

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY is set"
else
    echo -e "  ${YELLOW}⚠${NC} ANTHROPIC_API_KEY not set"
    echo ""
    echo "  Add to your shell profile (~/.bashrc or ~/.zshrc):"
    echo "    export ANTHROPIC_API_KEY='your-key-here'"
    echo "    export ANTHROPIC_BASE_URL='https://rdsec-aiendpoint.trendmicro.com/prod/aiendpoint/v1'"
    echo ""
    read -p "  Enter your API key now (or press Enter to skip): " API_KEY
    if [ -n "$API_KEY" ]; then
        SHELL_RC="$HOME/.bashrc"
        [ "$OS" == "mac" ] && SHELL_RC="$HOME/.zshrc"
        echo "" >> "$SHELL_RC"
        echo "# RDsec AI Endpoint (Trend Micro)" >> "$SHELL_RC"
        echo "export ANTHROPIC_API_KEY='$API_KEY'" >> "$SHELL_RC"
        echo "export ANTHROPIC_BASE_URL='https://rdsec-aiendpoint.trendmicro.com/prod/aiendpoint/v1'" >> "$SHELL_RC"
        echo -e "  ${GREEN}✓${NC} Added to $SHELL_RC (restart your shell or run: source $SHELL_RC)"
    fi
fi

# Step 4: MCP Servers
echo ""
echo -e "${BOLD}Step 4: MCP Servers${NC}"
echo ""
echo "Recommended MCP servers for the squad:"
echo ""
echo "  1. PX MCP (Vision One account provisioning)"
echo "     → Available from Ryan Duff / Callum Fiekert"
echo "     → Lets you rent V1 accounts, manage labs"
echo ""
echo "  2. V1 API MCP (Vision One API access)"
echo "     → Query detections, manage policies, XDR search"
echo "     → Needs V1 API key from your tenant"
echo ""
echo "  3. Filesystem MCP (local file access for Claude Code)"
echo "     → Built into Claude Code, no setup needed"
echo ""

# Step 5: Project structure
echo -e "${BOLD}Step 5: Project Structure${NC}"
echo ""

PROJECTS_DIR="$HOME/Documents/Projects"
[ "$OS" == "wsl" ] && PROJECTS_DIR="/mnt/c/Users/$USER/Documents/Projects"

echo "  Suggested project folder: $PROJECTS_DIR"
read -p "  Use this path? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    mkdir -p "$PROJECTS_DIR" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Created $PROJECTS_DIR"
fi

# Step 6: Quick test
echo ""
echo -e "${BOLD}Step 6: Quick Test${NC}"
echo ""

if command -v claude &>/dev/null && [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "  Testing Claude Code connection..."
    echo "Hello, respond with just 'Connected!'" | timeout 30 claude --print 2>/dev/null && {
        echo -e "  ${GREEN}✓${NC} Claude Code is working!"
    } || {
        echo -e "  ${YELLOW}⚠${NC} Connection test failed. Check your API key and base URL."
    }
else
    echo -e "  ${YELLOW}⚠${NC} Skipping test (Claude Code or API key not available)"
fi

# Summary
echo ""
echo "============================================"
echo -e "${BOLD}🌴 Setup Complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Get your RDsec API key if you don't have one"
echo "  2. Try: claude (opens interactive Claude Code)"
echo "  3. Try: claude 'What V1 products does Trend Micro offer?'"
echo "  4. Ask Joel or Coconut for help with MCP server setup"
echo ""
echo "Useful commands:"
echo "  claude                    # Interactive Claude Code"
echo "  claude --print 'query'   # One-shot query"
echo "  claude /mcp              # MCP server management"
echo ""
echo "Questions? Message Coconut in Teams or #coco-chat on Slack"
echo "============================================"
