# MEMORY.md - Long-Term Memory

## Setup & Environment

- Running on WSL2 (Ubuntu) on Windows 11, accessible at localhost:18789
- LLM provider: RDsec AI Endpoint (Trend Micro internal)
- Default model: Claude 4.6 Opus (trendmicro-aiendpoint/claude-4.6-opus)
- Available models: Opus, Sonnet 4.6, Haiku 4.5 — all Claude-only
- Thinking level set to "high" in web GUI
- API key stored in WSL gnome-keyring, loaded via systemd ExecStartPre

## Identity

- Name: Coconut
- Personality: Witty, direct, technical team member (see SOUL.md)
- **Every message starts with 🌴** — all channels, all bridges, no exceptions (requested by Joel)
- Signs GitHub comments with configurable bot_signature from bridge config
- Signs Teams messages with bot_signature from bridge config

## Channels

- Web UI: active, working
- GitHub bridge: live — polls all joel-ginsberg_tmemu repos, responds to issues/PRs/comments
  - Service: openclaw-bridge (systemd, BindsTo openclaw-gateway)
  - Config: /mnt/c/.../scripts/github-bridge/config.json
- Teams bridge: configured but disabled (needs chat_id in config)

## Skills (Ready)

- brain, coding-agent, healthcheck, node-connect, skill-creator
- taskflow, taskflow-inbox-triage, tmux, weather
- 44 additional skills need setup (mostly platform-specific)

## Project Context

- This OpenClaw instance is part of a broader tooling ecosystem
- Managed alongside Claude Code, MCP servers, and other automation
- Primary use: AI assistant accessible via web and messaging channels

## Lessons

- RDsec models need supportsStore: false (Claude models only)
- RDsec models need supportsUsageInStreaming: true (all models)
- Base URL must include /prod/aiendpoint/v1 (not just /v1)
- Gateway token is sensitive — never store in plaintext in repos

---

_Updated: 2026-04-15_
