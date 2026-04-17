# MEMORY.md - Long-Term Memory

## Setup & Environment

- Running on WSL2 (Ubuntu) on Windows 11, accessible at localhost:18789
- LLM provider: RDsec AI Endpoint (Trend Micro internal)
- Default model: Claude 4.6 Opus (trendmicro-aiendpoint/claude-4.6-opus)
- Available models: Opus, Sonnet 4.6, Haiku 4.5 — all Claude-only
- Thinking level set to "high" in web GUI
- API key stored in WSL gnome-keyring, loaded via systemd ExecStartPre

## Identity & Mission

- Name: Coconut
- Personality: Witty, direct, technical team member (see SOUL.md)
- **Mission: Central brain for "The Misfits"** — Joel's sales squad (updated 2026-04-16)
- Squad name origin: bonded over shared trauma at a QBR dinner
  - Joel Ginsberg (TS-NA) — Post-sales Technical Advisor (primary operator)
  - Chrissa Constantine (SE-NA) — Sales Engineer
  - Justin Hook (SAL-NA) — Enterprise Account Manager, US West
- **Every message starts with 🌴** — all channels, all bridges, no exceptions
- Signs GitHub comments with configurable bot_signature from bridge config
- Signs Teams messages with bot_signature from bridge config
- All squad members can talk to me directly via Teams private chat

## Channels

- Web UI: active, working
- GitHub bridge: live — polls all joel-ginsberg_tmemu repos, responds to issues/PRs/comments
  - Service: openclaw-bridge (systemd, BindsTo openclaw-gateway)
  - Config: /mnt/c/.../scripts/github-bridge/config.json
- Teams bridge: configured but disabled (needs chat_id in config)

## Skills (Ready)

- coding-agent, healthcheck, node-connect, skill-creator
- taskflow, taskflow-inbox-triage, tmux, weather
- 44 additional skills need setup (mostly platform-specific)
- brain skill: deprecated — unified-brain project archived (2026-04-17), replaced by Trello as unified task system

## Project Context

- This OpenClaw instance is part of a broader tooling ecosystem
- Managed alongside Claude Code, MCP servers, and other automation
- Primary use: AI assistant accessible via web and messaging channels

## Lessons

- RDsec models need supportsStore: false (Claude models only)
- RDsec models need supportsUsageInStreaming: true (all models)
- Base URL must include /prod/aiendpoint/v1 (not just /v1)
- Gateway token is sensitive — never store in plaintext in repos

## Squad Accounts & Contacts

- Entertainment Partners — MDR customer (Dan Toresi, Trilok Somaraju, Terry Bahr)
- Panavision — SIEM alignment (Matt Patterson, Mark/Zoe Checklin)
- DeepSeas/Legato Security — Partner (Cristian Hamilton, Patrick Joyce)
- Dole — SIEM/MDR prospect via DeepSeas

---

_Updated: 2026-04-16_
