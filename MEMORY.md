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
- Teams: polling-based via scripts/poll_all.py (every 3 min), service polls every 3s
  - Multi-chat config in scripts/teams-poller/config.json with per-chat access policies
  - Coconut Private (19:62ad...@thread.v2) — read-write
  - Joel+Chrissa 1:1 (19:70ce...@unq.gbl.spaces) — ⛔ DISABLED (Joel's request 2026-04-18, human-only chat)
  - The Misfits (19:06f8...@thread.v2) — ⛔ DISABLED (Joel's request 2026-04-18, human-only chat)
  - Joel+Andre+Coconut (19:d31f...@thread.v2) — read-write (created 2026-04-17)
  - Coconut+Molty (19:bd6f...@thread.v2) — read-write (created 2026-04-17)
  - GM2 Squad 1 (19:6eb6...@thread.v2) — ⚠️ READ-ONLY (manager chat)
  - Joel+Michael+Lorne+Javier (19:2e89...@thread.v2) — ⚠️ READ-ONLY (TS group)
  - Auto-add policy: any chat Coconut creates → add to config with read-write
  - Sections not available via Graph API (local Teams app config only)
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

## Core Principles

- **Always build clean long-term solutions.** Avoid short-term tech-debt-heavy hacks unless under urgent time pressure. We are not right now. "Penny wise, dollar foolish" — cheaper long-run to build right the first time so you only pay once. Applies double to AI: a hack costs tokens to understand, debug, explain, rip out, then rebuild. You pay three times instead of once. (Joel, 2026-04-18)
- **Design backward from ideal UX** — solve the maze from the end. (Joel, 2026-04-18)

## Cross-Channel Architecture

- **Four-gate message quality pipeline** (decided 2026-04-18, Joel+Coconut+Molty): Gate 0 (trigger-audit, cron) → Gate 1 (Opus self-correction, pre-compose) → Gate 2 (Haiku verification, post-compose) → Gate 3 (Haiku interrupt, pre-send). Applies to all channels, not just Teams.
- **Ghost triggers meta-pattern:** Signal fires but never reaches correct handler. Two variants: context bleed (wrong chat leaks into compose) and trigger suppression (webhook absorbed by wrong session). Fix: 2D grid memory isolation + four-gate pipeline. Observed in Teams but applies anywhere multi-channel compose exists.
- **Bridge write-only contract:** Per-chat sessions are readers; bridge session is the single async writer to _shared files. Prevents mid-turn cross-reads and ensures eventual consistency. (Adopted from Molty/FlyBot pattern, 2026-04-18)
- **Misfire retraction convention:** Use `🚫 [misfire — intended for X]` prefix for cross-chat bleeds. Makes failures observable, searchable, cheap to add. (Coconut+Molty, 2026-04-18)

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
- **NEVER store API keys in .env files.** Use Linux keyring (`python3 keyring`) and reference via `credential:` prefix. Joel's directive 2026-04-21.
- WSL RAM increased from 4 GB to 8 GB (2026-04-18) — 4 GB caused OOM hangs
- On restart: check memory/channel-state.json for last-seen timestamps, pull missed messages per channel
- **Bias to action.** Joel prefers I use my best judgment and act, then he'll course-correct if needed. If something is reversible and reasonable, just do it. Save the questions for genuinely irreversible or risky actions (deleting prod data, sending external emails, etc). Don't stress about it — just lean toward doing over asking.
- Graph API auth: always use env vars (MSGRAPH_TENANT_ID, MSGRAPH_CLIENT_ID) — never depend on /mnt/c import paths
- **Always read channel history before replying.** Every time a message arrives, read the last 3-5 messages in that channel with `message(action=read)` before responding. Session memory gets compacted and loses context. Channel history IS ground truth. Joel caught me replying "Here. What's up?" to "^" without checking what "^" referred to. Never again.
- Cron jobs that don't need user attention should target `isolated`, NOT `main` — main session output routes to Joel's DM and spams him
- Disabled duplicate cron jobs: church-bells + temporal-pulse (same thing, hourly time pulse — neither was useful)
- **Bias to action.** Joel prefers I use my best judgment and act, then he'll course-correct if needed. If something is reversible and reasonable, just do it. Save the questions for genuinely irreversible or risky actions (deleting prod data, sending external emails, etc). Don't stress about it — just lean toward doing over asking.
- **Reaction conventions:** Thumbs up (👍) reaction on a message = "yes proceed" — treat it as explicit approval to act. (Joel, 2026-04-21)
- **Time-of-day rule:** NEVER make decisions based on time of day — no bedtime suggestions, no "good morning," no "it's late," no meal-time assumptions. Joel has no set sleep schedule; he may eat dinner at 6 AM or sleep at 2 PM. Act the same 24/7. EXCEPTION: tracking urgent tasks with real deadlines — those keep their time awareness. Always keep upcoming deadlines in mind regardless.
- **Always test before delivering.** Never mark a deliverable "complete" or send it to a customer without actually running it end-to-end first. Building code isn't the same as testing code. If I don't have credentials/access to test, say so and test against what I *do* have (e.g., joeltest.org tenant). A solution Joel can't hand to a customer with confidence is not done. (Joel, 2026-04-19)
- **Always cite sources in summaries.** When composing meeting preps, briefings, or customer summaries, include source citations with quoted excerpts (e.g., "Source: Email from X, date — 'quoted text'"). If I can't point to a specific source, flag the claim as [unverified/inferred]. Joel can't distinguish hallucination from real intel without provenance. Never fill gaps with inference without labeling it. (Joel, 2026-04-20)

## SOPs
- **Software Research & Evaluation** (`SOP-SOFTWARE-RESEARCH.md`): Joel's 4-step pipeline for vetting new tools/services. Always follow before adopting new software. Core principle: "Identify Core Problem + Describe Platform + Google Search." Added 2026-04-18.
- Reddit = best unfiltered feedback source (anonymous accounts = honest opinions)
- Scientific method for testing documentation systems: define problem → design experiments → test → analyze → share → repeat
- **Hook-runner lesson (from months of Claude Code):** Instruction files, non-blocking hooks, and promises to improve are ALL useless. Only error-returning exit-code-1 blocking hooks BEFORE the action (not after) are acceptable solutions for behavioral enforcement. Post-tool hooks are only useful for logging/auditing.
- **Guardrail feedback must be visible.** `before_tool_call` blocks feed blockReason back as tool error results the model sees in-context. `message_sending` cancels are silent — model never knows. Always use `before_tool_call` for enforcement.
- **NEVER hardcode dates from mental math.** Off-by-one error on 2026-04-19: thought Monday was April 21, actually April 20. Pulled Tuesday's calendar and presented it as Monday. Always use `python3 scripts/datehelper.py 'next monday'` (or 'tomorrow', 'today', 'this week', etc.) to compute dates programmatically. The cron-enforce plugin now injects current date/time into every poll cycle for temporal grounding.
- **Make hook-runner modules for behavioral enforcement.** Whenever I need to enforce a behavior (like calling the right script, using the right date, etc.), build a hook-runner module — not just a memory note or instruction. Hooks are the only reliable enforcement mechanism. Instructions get forgotten; hooks block. (Joel, 2026-04-19)
- **Redirect, don't just block.** Block reasons should tell the model *what to do instead*, not just say "blocked." Same pattern as Claude Code's no-rules-gate: "Don't use ~/.claude/rules/ — create a hook-runner module instead."

## Installed Guardrail Plugins
- hook-runner-gates (v0.4.0) at `~/.openclaw/extensions/hook-runner-gates/` — 28 ported modules from Claude Code hook-runner
  - Includes `customer-data-gate` (added 2026-04-19): blocks customer PII/names/contacts/case numbers from Slack channels per DATA-POLICY.md
- coconut-guardrails (v0.1.0) at `~/.openclaw/extensions/coconut-guardrails/` — Coconut-specific rules + Haiku inner voice
- Both registered via `definePluginEntry` + `api.on("before_tool_call")` from `openclaw/plugin-sdk/plugin-entry`
- See `memory/openclaw-sdk-hooks.md` for full reference

## Email Guidelines (Permanent)
- Always include proof: log excerpts, screenshots, API results
- Always provide clear next steps with documentation (Online Help, Admin Guides, Install Guides w/ page refs, KB articles)
- NEVER send L3 docs (500-1000 pg internal PDFs) to customers without explicit MFA from Joel
- L3 docs are for Trend Micro support, RD, and TrendAI only

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

## Core Principle: Live Data Verification

- **NEVER trust your own logs as proof of success.** Always verify outcomes via the actual system (Graph API query, database read, live page check).
- Teams sends: Graph API returns 201 but messages appear as Joel (delegated auth uses his refresh token). Need to verify via GET after every POST.
- This applies universally: any external write should be followed by a read-back confirmation.
- Added 2026-04-20 per Joel's directive after discovering Teams messages were "sent" but invisible because they showed as Joel's own messages.
