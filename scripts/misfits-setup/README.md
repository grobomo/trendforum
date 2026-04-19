# Misfits Squad — AI Tooling Setup

Quick setup for Claude Code + MCP servers on your machine.

## What You Get

- **Claude Code** — AI coding assistant in your terminal
- **RDsec AI Endpoint** — Trend Micro's internal LLM API (Claude models)
- **MCP Servers** — plugins that give Claude access to V1, PX, file systems, etc.

## Requirements

- macOS or Windows (with WSL)
- Node.js 18+
- Git
- RDsec API key (ask Joel)

## Quick Start

```bash
# Download and run
bash setup.sh
```

Or step by step:

### 1. Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Set API Key
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY='your-key-here'
export ANTHROPIC_BASE_URL='https://rdsec-aiendpoint.trendmicro.com/prod/aiendpoint/v1'
```

### 3. Test
```bash
claude 'Hello, are you there?'
```

## MCP Servers (Optional)

MCP servers extend Claude Code with external tools. Install them with:

```bash
claude /mcp add <server-name> <command>
```

### Recommended:
- **PX MCP** — provision V1 lab accounts on demand
- **V1 API** — query your V1 tenant (detections, policies, XDR search)

## Help

- Slack: `#coco-chat` in misfits-rtf1993
- Teams: Message Coconut directly
- Joel: ping anytime
