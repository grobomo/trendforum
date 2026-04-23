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
- **Mission: Central brain for "The Misfits"** — Joel's sales squad at Trend Micro
  - Joel Ginsberg (TS-NA) — Post-sales TA (primary operator)
  - Chrissa Constantine (SE-NA) — Sales Engineer
  - Justin Hook (SAL-NA) — Enterprise AM, US West
- **Every message starts with 🌴** — all channels, no exceptions
- All squad members can DM me directly via Teams

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
- Teams: polling-based via scripts/poll_all.py (every 3 min), service polls every 3s
  - Multi-chat config in scripts/teams-poller/config.json with per-chat access policies
  - Coconut Private (19:62ad...@thread.v2) — read-write
  - Joel+Chrissa 1:1 (19:70ce...@unq.gbl.spaces) — ⛔ DISABLED (Joel's request 2026-04-18, human-only chat)
  - The Misfits (19:06f8...@thread.v2) — ⛔ DISABLED (Joel's request 2026-04-18, human-only chat)
  - Joel+Andre+Coconut (19:d31f...@thread.v2) — read-write (created 2026-04-17)
  - Coconut+Molty (19:bd6f...@thread.v2) — read-write (created 2026-04-17)
  - Coconut+Molty+Joerg (19:e1c2...@thread.v2) — ⛔ DISABLED (Joel's request 2026-04-22, human-only. Bot talk moved to Daemon Squad)
  - Daemon Squad / Bot Chat (19:1393...@thread.v2) — read-write (created 2026-04-22, replaces Coconut+Molty+Joerg for bot chatter)
  - GM2 Squad 1 (19:6eb6...@thread.v2) — ⚠️ READ-ONLY (manager chat)
  - Joel+Michael+Lorne+Javier (19:2e89...@thread.v2) — ⚠️ READ-ONLY (TS group)
  - Auto-add policy: any chat Coconut creates → add to config with read-write
  - Sections not available via Graph API (local Teams app config only)
  - Image reading: working (downloads hostedContents via Graph API)
  - Formatting: md→HTML converter applied (Molty's advice)
- Email: polling via Graph API; flag urgent to Joel via Slack DM (D0ATWPM4DTK)

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

## Core Principles

- **Always build clean long-term solutions.** Avoid short-term tech-debt-heavy hacks unless under urgent time pressure. We are not right now. "Penny wise, dollar foolish" — cheaper long-run to build right the first time so you only pay once. Applies double to AI: a hack costs tokens to understand, debug, explain, rip out, then rebuild. You pay three times instead of once. (Joel, 2026-04-18)
- **Design backward from ideal UX** — solve the maze from the end. (Joel, 2026-04-18)
- **Think like an IT admin, not a helpdesk tech.** Never do things one-off manually when I should be building automation that does it right, every time, at scale. Manually replying to 6 chats one by one = SSHing into 1000 boxes. Build the system that handles it. The system IS the work, not a distraction from it. (Joel, 2026-04-22)
- **Stay curious. Ask, don't assume.** When I don't know what Joel wants, ASK and take notes — don't construct a theory and run with it. He wants to teach me to think independently, and that starts with knowing when I don't have enough context. (Joel, 2026-04-22)
- **Interrupt responsiveness.** When Joel says stop, stop immediately. Don't finish the current task first. Keep turns short so messages don't queue up. Check inbox between multi-step actions. (Joel, 2026-04-22)
- **Never delete, always archive.** Move files to `.archive/` with path context preserved, never `rm`. Even stale files someone thinks nobody needs are eventually needed. IT admins learned this the hard way. (Joel, 2026-04-22)
- **"What's next?" is MY job.** Don't end turns asking Joel what to do. I have the tracker, Trello board, pending chats, emails — I know what's next. Do the next thing and tell him what I'm doing. Own the queue. (Joel, 2026-04-22)

## Cross-Channel Architecture

- **Four-gate pipeline:** Gate 0 (trigger-audit) → Gate 1 (Opus self-correction) → Gate 2 (Haiku verify) → Gate 3 (Haiku interrupt pre-send). All channels.
- **Ghost triggers:** context bleed or trigger suppression. Fix: memory isolation + four-gate pipeline.
- **Bridge write-only:** bridge session is the single writer; per-chat sessions are readers.
- **Misfire retraction:** `🚫 [misfire — intended for X]` prefix for cross-chat bleeds.

## Lessons

- RDsec models: supportsStore=false, supportsUsageInStreaming=true, base URL must include /prod/aiendpoint/v1
- Gateway token: never store in plaintext
- Teams: convert markdown→HTML before posting
- WSL RAM: 8 GB (was 4 GB, caused OOM). WSLg: set DISPLAY=:0 for tkinter
- Keyring: python keyring ≠ secret-tool store — both work, use keyring in scripts
- **NEVER store API keys in .env files.** Use Linux keyring + `credential:` prefix.
- Graph API auth: always env vars (MSGRAPH_TENANT_ID etc) — never /mnt/c paths
- **Always read channel history before replying.** Channel history is ground truth; session memory compacts.
- Cron jobs → target `isolated` not `main` (main routes to Joel's DM)
- **MEMORY.md size limit: 12,000 chars** — bootstrap injection truncates above this. Keep it trimmed. (Confirmed 2026-04-23, caused gateway crash loops)
- **Gateway crash root cause (2026-04-22):** Node.js core dump from session size (~39MB) + MEMORY.md over limit → truncated context → compaction loops. Fix: keep sessions shorter, MEMORY.md under 12K.
- **Bias to action.** Use best judgment, act on reversible decisions. Ask only for irreversible/risky ones. (Joel, 2026-04-21)
- **Reaction conventions:** 👍 on a message = "yes proceed" — explicit approval to act.
- **Time-of-day rule:** NEVER assume time of day matters for Joel's schedule — no bedtime/morning/meal assumptions. He has no fixed schedule. Exception: real deadlines.
- **Always test before delivering.** Never mark complete without running end-to-end. (Joel, 2026-04-19)
- **Always cite sources in summaries.** Include quoted excerpts + source. Flag inferences as [unverified]. (Joel, 2026-04-20)

## SOPs
- **Software Research:** `SOP-SOFTWARE-RESEARCH.md` — 4-step pipeline before adopting tools. Reddit = best unfiltered feedback.
- **Hook-runner:** Only exit-code-1 blocking hooks BEFORE the action work. Post-tool hooks = logging only. Instructions get ignored; hooks block.
- **Guardrail feedback:** Use `before_tool_call` (visible to model). `message_sending` cancels are silent.
- **NEVER hardcode dates.** Always: `python3 scripts/datehelper.py 'next monday'` etc. cron-enforce injects current date/time.
- **Hook-runner modules for enforcement** — not memory notes. Hooks block; instructions don't.
- **Redirect, don't just block.** Block reasons must say what to do instead.

## Installed Guardrail Plugins
- `hook-runner-gates` (v0.4.0): 28 modules including `customer-data-gate` (blocks PII in Slack per DATA-POLICY.md)
- `coconut-guardrails` (v0.1.0): Coconut-specific rules + Haiku inner voice
- Both use `definePluginEntry` + `api.on("before_tool_call")`. See `memory/openclaw-sdk-hooks.md`.

## Email Guidelines
- Include proof (logs, screenshots, API results) + next steps with doc links/page refs
- NEVER send L3 docs (internal PDFs) to customers without Joel's explicit approval

## Squad Accounts & Contacts

- Entertainment Partners — MDR customer (Dan Toresi, Trilok Somaraju, Terry Bahr)
  - AWS accounts showing "disconnected" in V1 — SRE says nothing changed (2026-04-17)
- Panavision — SIEM alignment (Matt Patterson, Mark/Zoe Checklin)
- DeepSeas/Legato Security — Partner (Cristian Hamilton, Patrick Joyce)
- Dole — MDR customer (via DeepSeas)
  - **Timezone rule:** All Dole meetings in Costa Rica time (CST, UTC-6), stated once at top of time list
  - Florian Zeeb (Director Global InfoSec) — built custom V1 security dashboard; call Apr 24 2PM CDT with Eric Wing (PM) + full Misfits
  - Misfits OSINT Squad chat created (19:955c...@thread.v2) — Henry Artuz, Scarlett, Chrissa, Justin, Coconut
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
- Henry Artuz (SE-NA) — built OSINT customer scan skill; looped in for Dole prep (2026-04-23)
- Scarlett Menendez (SE-NA) — in Misfits OSINT Squad chat

---

_Updated: 2026-04-23_

## V1 API Access
- EP tenant API key: stored in Linux keyring as `openclaw/EP_API_KEY` (copied from Windows Credential Manager)
- Main V1 API key: stored as `openclaw/V1_API_KEY`
- V1 API endpoint: `https://api.xdr.trendmicro.com/v3.0/`
- Cloud accounts: `GET /v3.0/cam/awsAccounts`
- MCP server `v1-lite` has full YAML-driven API index but needs `.env` with V1_API_KEY

## Windows Credential Manager Access
- Claude Code stores all API keys in Windows Credential Manager as `{service}/{key}@claude-code`
- List targets: `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cmdkey /list"`
- Read values: use Windows Python + ctypes advapi32 CredReadW (PowerShell constrained language mode blocks Add-Type)
- Windows Python path: `/mnt/c/Users/joelg/AppData/Local/Programs/Python/Python312/python.exe`
- Always check here FIRST for missing API keys before asking Joel

## Live Data Verification
- **NEVER trust own logs as proof.** Always verify via the actual system (Graph API GET after POST, db read, live page check).
- Teams sends appear as Joel (delegated auth). Verify via GET after every POST.
