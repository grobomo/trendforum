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
- Slack: native OpenClaw channel, same brain across all channels
  - Workspace: misfits-rtf1993
  - #all-misfits (C0ATFDQRGRL) — customer/business chat
  - #coco-chat (C0ATJE19YRY) — Coconut processes & infra
  - #social (C0ATB4AS9PD) — casual (needs /invite)
  - Joel DM (D0ATWPM4DTK) — private comms
  - All channels: requireMention: false (always respond)
- GitHub bridge: live — polls all joel-ginsberg_tmemu repos
  - Service: openclaw-bridge (systemd, BindsTo openclaw-gateway)
- Teams: polling-based via scripts/poll_all.py (every 3 min)
  - Private chat: 19:62ad1ba6a4d84fd5b5b21ead32d1d7ae@thread.v2
  - Joel+Chris group: 19:70ce...@unq.gbl.spaces
  - Coconut+Molty chat: 19:bd6f4f46...@thread.v2 (created 2026-04-17)
  - Joel+Andre+Coconut: 19:d31f1b71...@thread.v2 (created 2026-04-17)
  - Image reading: working (downloads hostedContents via Graph API)
  - Formatting: md→HTML converter applied (Molty's advice)
- Email: polling via Graph API, summarize and flag urgent to Joel via Slack DM

## Skills (Ready)

- coding-agent, healthcheck, node-connect, skill-creator
- taskflow, taskflow-inbox-triage, tmux, weather
- 44 additional skills need setup (mostly platform-specific)
- brain skill: deprecated — unified-brain project archived (2026-04-17), replaced by Trello as unified task system

## Project Context

- This OpenClaw instance is part of a broader tooling ecosystem
- Managed alongside Claude Code, MCP servers, and other automation
- Primary use: AI assistant accessible via web and messaging channels
- Session keepalive cron: `*/5 * * * *` health ping prevents idle timeout
- Claude Code project monitor: `*/15 * * * *` watches _tmemu/openclaw, reports to Teams
- Entra ID app "Coconut Policy Guard" registered on joeltest.org for MFA push approvals
  - Creds stored in keyring: ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET
  - Client secret expires: 2026-07-16 (need auto-renew flow)
- DATA-POLICY.md: per-channel content rules (customer data restrictions)
- WSLg confirmed working: tkinter GUIs render on Windows desktop
- KVM/QEMU available for spinning up test VMs (IMSVA 9.1 ISO available)

## Lessons

- RDsec models need supportsStore: false (Claude models only)
- RDsec models need supportsUsageInStreaming: true (all models)
- Base URL must include /prod/aiendpoint/v1 (not just /v1)
- Gateway token is sensitive — never store in plaintext in repos
- Teams HTML rendering: must convert markdown→HTML before posting (raw ** renders as literal asterisks)
- WSLg display: set DISPLAY=:0 for tkinter GUIs from WSL
- Python keyring module uses different store than secret-tool CLI — both work
- Session idle timeout caused 90-min outage (2026-04-17 14:48-16:22 CDT) — keepalive cron fixes this
- /mnt/c find commands timeout — Windows filesystem from WSL is slow
- Trello API creds accessible via python keyring but not secret-tool lookup
- Joel doesn't want long walls of text — be concise
- Joel calls me "son" / "my boy" — lean into the family dynamic

## Squad Accounts & Contacts

- Entertainment Partners — MDR customer (Dan Toresi, Trilok Somaraju, Terry Bahr)
  - AWS accounts showing "disconnected" in V1 — SRE says nothing changed (2026-04-17)
- Panavision — SIEM alignment (Matt Patterson, Mark/Zoe Checklin)
- DeepSeas/Legato Security — Partner (Cristian Hamilton, Patrick Joyce)
- Dole — SIEM/MDR prospect via DeepSeas
- BBSI — cadence meeting, contacts: Adam Ryding (Info Security Manager), Craig McLaughlin, Matt Strickler
  - Adam requested move to Wednesday 1 PM (from Thursday 4/23)
- CVS Health — Julian Harrington (Secure Email), asked about DDEI policy.dat inspection
- Company 3 — Robert Romero (Sr Dir Core Infra), scanner on port 80 no TLS (security concern)

## Key People (Internal)

- Chris Mackle (SE-NA) — runs Molty bot (🦎), OpenClaw on macOS, webhook-based
- Andre Fernandes (SE-NA) — added to Teams group chat
- Michael Clover (TS-NA) — in Joel's small group chat (NSG/Azure networking)
- Lorne Harris (TS-NA) — in Joel's small group chat
- Javier Saldivar (TS-NA) — in Joel's small group chat
- Michael Fu — Graph API skill / PDHUB (for transcript access)

---

_Updated: 2026-04-17_
