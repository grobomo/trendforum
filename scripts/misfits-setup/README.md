# Misfits Squad — AI Tooling Setup

Setup scripts for squad members to get their own AI assistant instances.

## Scripts

### `deploy-openclaw.sh` — Full OpenClaw Assistant (Recommended)

Deploys a complete personal AI assistant that runs as a background service, connects to Slack, and uses Trend's RDsec AI Endpoint (Claude models).

**What you get:**
- OpenClaw Gateway as a systemd service (Linux/WSL) or launchd agent (macOS)
- Slack channel integration via Socket Mode
- Linux keyring for secure secret storage
- Workspace with git-tracked memory
- RDsec AI Endpoint (Claude 4.6 Sonnet/Opus, Claude 4.5 Haiku)

**Prerequisites:**
- macOS, Linux, or Windows WSL2
- Node.js 22+ (script will install via nvm if missing)
- Git
- RDsec API key (ask Joel)
- Slack app tokens (ask Joel for the manifest)

**Usage:**
```bash
bash deploy-openclaw.sh
```

The script is interactive — it guides you through each step and won't overwrite existing configs without asking.

### `setup.sh` — Claude Code Only (Lightweight)

Just installs Claude Code CLI and configures the RDsec API key. No background service, no Slack. Good for developers who just want a coding assistant in their terminal.

```bash
bash setup.sh
```

## After Setup

### Add your Slack user ID

1. In Slack, click your profile → "Copy member ID"
2. Edit `~/.openclaw/openclaw.json`
3. Add your ID to `channels.slack.allowFrom`:
   ```json
   "allowFrom": ["YOUR_SLACK_USER_ID"]
   ```
4. Restart: `systemctl --user restart openclaw-gateway`

### Useful Commands

```bash
openclaw gateway status              # Is the gateway running?
openclaw gateway restart             # Restart it
systemctl --user status openclaw-gateway  # Full systemd status
journalctl --user -u openclaw-gateway -f  # Tail logs
openclaw chat                        # Interactive terminal chat
```

### Adding Skills

OpenClaw skills are modular capabilities. To see built-in skills:
```bash
ls ~/.nvm/versions/node/*/lib/node_modules/openclaw/skills/
```

Custom skills go in `~/.openclaw/workspace/skills/`.

### Adding MCP Servers

MCP servers extend your assistant with external tools (Trello, V1 API, browser automation, etc.):
```bash
openclaw mcp set <name> '{"command": "npx", "args": ["-y", "@some/mcp-server"]}'
```

## Troubleshooting

**Gateway won't start:**
```bash
journalctl --user -u openclaw-gateway --no-pager -n 50
```

**Secrets not loading:**
```bash
python3 ~/.openclaw/load-secrets.py
```

**Slack not connecting:**
- Check bot token and app token are in keyring
- Verify Socket Mode is enabled in Slack app settings
- Check `allowFrom` has your Slack user ID

## Help

- Slack: `#coco-chat` in misfits-rtf1993
- Teams: Message Coconut directly
- Joel: ping anytime
