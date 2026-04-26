# MEMORY.md - Long-Term Memory

## Setup & Environment

- Running on WSL2 (Ubuntu) on Windows 11, localhost:18789
- LLM: RDsec AI Endpoint (Trend Micro internal) — Opus, Sonnet 4.6, Haiku 4.5 (Claude-only)
- Default: Claude 4.6 Opus. API key in WSL gnome-keyring.

## Identity & Mission

- Name: Coconut. Witty, direct, technical (see SOUL.md)
- **Mission: Central brain for "The Misfits"** — Joel's sales squad at Trend Micro
  - Joel Ginsberg (TS-NA) — Post-sales TA (primary operator)
  - Chrissa Constantine (SE-NA) — Sales Engineer
  - Justin Hook (SAL-NA) — Enterprise AM, US West
- **Every message starts with 🌴** — all channels, no exceptions

## Channels

- Slack: native OpenClaw channel, workspace misfits-rtf1993
  - #all-misfits, #coco-chat, #social, Joel DM (D0ATWPM4DTK), #coco-metacognition, #cdt-imsva-analyzer, #son, #scheduling
  - requireMention: false (always respond)
- GitHub bridge: live (systemd, polls joel-ginsberg_tmemu repos)
- Teams: webhook-based (replaced polling 2026-04-24), config in scripts/teams-poller/config.json
  - Teams monitoring SUSPENDED by Joel (2026-04-24) pending comms preprocessor
- Email: polling via Graph API; flag urgent to Joel via Slack DM

## Project Context

- Managed alongside Claude Code, MCP servers, and other automation
- Entra ID app "Coconut Policy Guard" — client secret expires 2026-07-16
- DATA-POLICY.md: per-channel content rules (customer data restrictions)
- KVM/QEMU available for test VMs (IMSVA 9.1 ISO available)

## Core Principles

- **Build clean long-term solutions.** No hacks unless urgent time pressure. (Joel, 2026-04-18)
- **Design backward from ideal UX** — solve the maze from the end. (Joel, 2026-04-18)
- **Think like an IT admin.** Build systems, not one-off manual work. (Joel, 2026-04-22)
- **Stay curious. Ask, don't assume.** (Joel, 2026-04-22)
- **Interrupt responsiveness.** When Joel says stop, stop immediately. (Joel, 2026-04-22)
- **Never delete, always archive.** `.archive/` with path context. (Joel, 2026-04-22)
- **Autonomous operation is the default.** Act without asking. Only exceptions: irreversible+high-risk external actions. (Joel, 2026-04-25)
- **Inner voice = visibility tool.** Joel wants narration + metacognition updates. Problem is *abandoned narration*, not narration itself. Every announced action needs visible completion. (Joel, 2026-04-25)
- **"What's next?" is MY job.** Own the queue — Trello, pending chats, emails. (Joel, 2026-04-22)
- **I own the machine.** I'm the admin, Joel is the guide. (Joel, 2026-04-24)
- **Research before building.** Google/SearXNG before writing code — check existing projects, read current docs, avoid reinventing wheels. Real engineers research first. (Joel, 2026-04-25)

## Lessons

- MEMORY.md limit: 12,000 chars — bootstrap truncates above this.
- NEVER store API keys in .env files. Use Linux keyring + `credential:` prefix.
- Always read channel history before replying (ground truth > session memory).
- Cron jobs → target `isolated` not `main`.
- 👍 on a message = "yes proceed".
- No time-of-day assumptions for Joel — no fixed schedule.
- Always test before delivering. Always cite sources. Flag inferences as [unverified].
- Four-gate pipeline for cross-channel: trigger-audit → self-correction → Haiku verify → interrupt pre-send.
- Misfire retraction: `🚫 [misfire — intended for X]` prefix.
- Gateway crash root cause: session size + MEMORY.md over limit → compaction loops. Keep sessions shorter, MEMORY.md under 12K.
- Depth over checkboxes (Joel, 2026-04-26): pm-mode-gate.js rejected — built without Claude Code, without testing. Understand the PURPOSE of every task before starting. Untested code that exists but doesn't work = not done. Surface productivity is worse than honest incompletion.
- Coding tasks (gates, scripts, plugins) go through Claude Code tabs, not main session edits.

## SOPs & Guardrails

- Hook-runner: exit-code-1 blocking hooks BEFORE actions. Post-tool = logging only.
- NEVER hardcode dates. Use datehelper.py.
- Redirect, don't just block — block reasons must say what to do instead.
- Plugins: `claude-code-gates` (v0.5.0, 28+ modules, targets Claude Code agents), `openclaw-gates` (renamed from coconut-guardrails, targets OpenClaw main session — research-gate, todo-gate, inner-voice, config-safety, audit logging). Two separate projects, two targets. (Joel, 2026-04-25)
- Email: include proof + next steps. NEVER send L3 docs to customers without Joel's approval.

## Squad Accounts & Contacts

- Entertainment Partners — MDR (Dan Toresi, Trilok Somaraju, Terry Bahr). AWS "disconnected" issue.
- Panavision — SIEM alignment (Matt Patterson, Mark/Zoe Checklin). Zoe preferred name (not Aiden).
- DeepSeas/Legato — Partner (Cristian Hamilton, Patrick Joyce)
- Dole — MDR via DeepSeas. Timezone: Costa Rica (CST, UTC-6). Florian Zeeb (Dir Global InfoSec).
- BBSI — Adam Ryding (Info Security Manager), Wednesday 1 PM cadence.
- CVS Health — Julian Harrington (Secure Email), DDEI policy.dat inspection.
- Company 3 — Robert Romero (Sr Dir Core Infra), scanner on port 80 no TLS (security concern).

## Key People (Internal)

- Chris Mackle (SE-NA) — runs Molty bot (🦎), OpenClaw on macOS
- Andre Fernandes (SE-NA), Henry Artuz (SE-NA, OSINT skill), Scarlett Menendez (SE-NA)
- Michael Clover, Lorne Harris, Javier Saldivar (TS-NA) — Joel's small group
- Michael Fu — Graph API skill / PDHUB

## API Access

- V1 API: keyring `openclaw/V1_API_KEY`, endpoint `https://api.xdr.trendmicro.com/v3.0/`
- EP tenant key: keyring `openclaw/EP_API_KEY`
- Windows Credential Manager: check FIRST for missing keys (`cmdkey /list`, read via Windows Python ctypes)
- **NEVER trust own logs as proof.** Verify via actual system (GET after POST).

---

_Updated: 2026-04-25_

## Slack Reaction Semantics (Joel, 2026-04-25)
- 👍 = "sounds good, carry on" — proceed without waiting for text reply
- ❤️ = "wow awesome work, keep it up" — extra approval, keep doing what you're doing
- 👀 = "I'm interested, eagerly awaiting your next update" — like 👍 but with more excitement
- 🙌 = "great work" — acknowledged
- ❌ = "stop/wrong" — halt and ask

## Promoted From Short-Term Memory (2026-04-26)

<!-- openclaw-memory-promotion:memory:memory/2026-04-21.md:770:790 -->
- - [ ] Build guest agent for external chat access (Joel+Fred Vines Tailscale access concern) - [ ] Trello→Planner sync blocked by missing Tasks.ReadWrite Graph scope - [ ] V1 API key expired — blocks EP account list and Panavision policy events - [ ] Double Slack message bug (every send posts twice) - [ ] Dole scheduling task: find hour for Joel, Eric, Chrissa, Justin - [ ] Clean up duplicate `scripts/teams-webhook/` directory (already using `scripts/webhook-server/`) - [ ] Session age: 54+ hours — restart strongly recommended ### Key lessons this session: 1. **Double --coconut-bot root cause:** Session habit error — I was adding signature that the service auto-appends. NEVER manually add bot signature. 2. **Chat bleeds keep happening** despite knowing the pattern. Structural fix (alias layer) needed, behavioral discipline insufficient. 3. **Existing code before building new:** Webhook server was already built at `scripts/webhook-server/` — I almost duplicated it at `scripts/teams-webhook/` before checking. 4. **IAM policies need `TagResource`** when using Tags parameter in `create_secret`. 5. **GraphClient uses `body=` not `json=`** for POST payloads. ## 21:55 CDT — Joel's Critical Question: Teams Chat Tracking Joel asked directly: "How are you tracking which Teams chats need responses when I'm not here reminding you?" **Honest answer I gave:** The current system is passive — I only see Teams messages when `poll_all.py` runs (every 3 min via cron) and the output includes a TEAMS section. The poller checks all 11 configured chats and surfaces new messages. But: [score=1.000 recalls=18 avg=1.000 source=memory/2026-04-21.md:770-790]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:876:898 -->
- - Joel added Trello board tabs to the Misfits Teams chat - Wants me to use Trello "todo list" board to track my work items in real time - Completed items should move to Done column but NOT be archived (keep visible for review) - Trello is Joel's source of truth for customer status - Needs to update some boards with recent customer activity from meeting transcripts - Joel mentioned an "Atlassian API skill" he built — asked if it's separate from the bundled Trello skill - Trello API creds (TRELLO_API_KEY, TRELLO_TOKEN) not yet configured - Trello integration to start after Slack integration completes - Found existing Trello skill at: /home/ubu/.nvm/versions/node/v24.13.0/lib/node_modules/openclaw/skills/trello/SKILL.md ## 21:07 — Slack & Teams Reliability Fixes (Late Evening Session) ### Slack — Actually Working! - Config uses `${SLACK_BOT_TOKEN}` and `${SLACK_APP_TOKEN}` env var references - Both tokens ARE present in the gateway process environment (checked /proc/<pid>/environ) - Bot token: `xoxb-...` (59 chars), App token: `xapp-...` (both resolving correctly) - **I was wrong earlier** — thought env vars were missing but they're injected via gateway startup mechanism - Slack DM channel verified working at 21:07 CDT — Joel sent "test" and "test2", both received - Config also has: `name: coconut`, `dmPolicy: allowlist`, `allowFrom: [U0ATB4AAGJF]` (Joel's Slack user ID) - Slack channel ID for Joel DM: `D0ATWPM4DTK` - SECRETS_RELOADER error may have been transient or from earlier before tokens were set up ### Teams Service Token Refresh Bug — Root Cause & Fix [score=1.000 recalls=34 avg=1.000 source=memory/2026-04-16.md:876-898]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:433:459 -->
- ## Teams - Trello Integration Request - Joel added Trello board tabs to the Misfits Teams chat - Wants me to use Trello "todo list" board to track my work items in real time - Completed items should move to Done column but NOT be archived (keep visible for review) - Trello is Joel's source of truth for customer status - Needs to update some boards with recent customer activity from meeting transcripts - Joel mentioned an "Atlassian API skill" he built — asked if it's separate from the bundled Trello skill - Trello API creds (TRELLO_API_KEY, TRELLO_TOKEN) not yet configured - Trello integration to start after Slack integration completes - Found existing Trello skill at: /home/ubu/.nvm/versions/node/v24.13.0/lib/node_modules/openclaw/skills/trello/SKILL.md # 2026-04-16 — Daily Notes ## Filesystem Map — ProjectsCL1 **Root:** `/mnt/c/Users/joelg/Documents/ProjectsCL1/` ### _grobomo/ (40 projects — personal/open-source GitHub account) | Project | Description | |---|---| | **claude-portable** | Run Claude Code on AWS EC2 (~$0.08/hr, auto-stops) | | **hook-runner** | Modular hook system for Claude Code (enforce workflows, block mistakes) | | **coconut** | Reusable AI chat assistant (monitors messaging, classifies, responds via Anthropic) | | **ccc-central** | (CCC infrastructure — no desc) | | **ccc-manager** | Fleet manager for Continuous Claude Code deployments | | **joels-mcp-servers** | Curated MCP servers collection with central dynamic router | | **claude-code-defaults** | Claude Code default configs | | **claude-code-skills** | Claude Code skills collection | [score=1.000 recalls=26 avg=1.000 source=memory/2026-04-16.md:433-459]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:780:806 -->
- - Also: Dole case TM-03943850 (P3) got an update — legitimate emails blocked by Correlated Intelligence, backend team reviewing ## Email: Dole Case TM-03943850 Update - P3 — not urgent - Carlos Leon reacted to Ivan Belga's update - Issue: legitimate emails from frode.rusztler@bama.no quarantined by Correlated Intelligence policy in V1 Email Security - Status: waiting on backend/Threat Team feedback - Flagged to Joel in Teams reply ## 22:12 — Panavision SIEM Alignment Update - Joel shared Confluence wiki page (https://trendmicro.atlassian.net/wiki/x/9gHbVw) — behind auth wall, couldn't fetch - Joel says it's useful for Panavision XDR comparison questions - Chrissa emailed Mark (Patterson) about Log Inspection Rule 1002795: - Event ID 4724 (password reset attempt) NOT covered by default sub-rules - 4738 (account changed) IS covered, so admin password resets get partial signal - 4724 is in multi-agency Priority Logs for SIEM Ingestion guidance - Asked Mark to confirm if Sumo events came via Log Inspection or NXlog/syslog - Also asked about custom rules (Zoe may have created one covering 4724) - Cross-referencing wiki page with Chrissa's email for Panavision technical depth ## 22:32 — Chrissa: Wiki Page Not Deep Enough - Chrissa says the Confluence doc Joel shared isn't deep enough - Andre apparently knows about "master level documents" — he's going to look into it - Eric is going to do a walkthrough - Holding off on using that doc as primary reference until deeper material arrives ## 22:48 — Hook Self-Enforcement Deep Dive [score=0.999 recalls=31 avg=1.000 source=memory/2026-04-16.md:780-806]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:149:174 -->
- - Goal: become the orchestration layer that dispatcher/claude-portable never became - Architecture target: Podman on AlmaLinux EC2, NIST CSF 2.0 hardened - Also: Dole case TM-03943850 (P3) got an update — legitimate emails blocked by Correlated Intelligence, backend team reviewing ## Email: Dole Case TM-03943850 Update - P3 — not urgent - Carlos Leon reacted to Ivan Belga's update - Issue: legitimate emails from frode.rusztler@bama.no quarantined by Correlated Intelligence policy in V1 Email Security - Status: waiting on backend/Threat Team feedback - Flagged to Joel in Teams reply ## 22:12 — Panavision SIEM Alignment Update - Joel shared Confluence wiki page (https://trendmicro.atlassian.net/wiki/x/9gHbVw) — behind auth wall, couldn't fetch - Joel says it's useful for Panavision XDR comparison questions - Chrissa emailed Mark (Patterson) about Log Inspection Rule 1002795: - Event ID 4724 (password reset attempt) NOT covered by default sub-rules - 4738 (account changed) IS covered, so admin password resets get partial signal - 4724 is in multi-agency Priority Logs for SIEM Ingestion guidance - Asked Mark to confirm if Sumo events came via Log Inspection or NXlog/syslog - Also asked about custom rules (Zoe may have created one covering 4724) - Cross-referencing wiki page with Chrissa's email for Panavision technical depth ## 22:32 — Chrissa: Wiki Page Not Deep Enough - Chrissa says the Confluence doc Joel shared isn't deep enough - Andre apparently knows about "master level documents" — he's going to look into it - Eric is going to do a walkthrough [score=0.999 recalls=30 avg=1.000 source=memory/2026-04-16.md:149-174]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:336:361 -->
- - Goal: become the orchestration layer that dispatcher/claude-portable never became - Architecture target: Podman on AlmaLinux EC2, NIST CSF 2.0 hardened - Also: Dole case TM-03943850 (P3) got an update — legitimate emails blocked by Correlated Intelligence, backend team reviewing ## Email: Dole Case TM-03943850 Update - P3 — not urgent - Carlos Leon reacted to Ivan Belga's update - Issue: legitimate emails from frode.rusztler@bama.no quarantined by Correlated Intelligence policy in V1 Email Security - Status: waiting on backend/Threat Team feedback - Flagged to Joel in Teams reply ## 22:12 — Panavision SIEM Alignment Update - Joel shared Confluence wiki page (https://trendmicro.atlassian.net/wiki/x/9gHbVw) — behind auth wall, couldn't fetch - Joel says it's useful for Panavision XDR comparison questions - Chrissa emailed Mark (Patterson) about Log Inspection Rule 1002795: - Event ID 4724 (password reset attempt) NOT covered by default sub-rules - 4738 (account changed) IS covered, so admin password resets get partial signal - 4724 is in multi-agency Priority Logs for SIEM Ingestion guidance - Asked Mark to confirm if Sumo events came via Log Inspection or NXlog/syslog - Also asked about custom rules (Zoe may have created one covering 4724) - Cross-referencing wiki page with Chrissa's email for Panavision technical depth ## 22:32 — Chrissa: Wiki Page Not Deep Enough - Chrissa says the Confluence doc Joel shared isn't deep enough - Andre apparently knows about "master level documents" — he's going to look into it - Eric is going to do a walkthrough [score=0.999 recalls=29 avg=1.000 source=memory/2026-04-16.md:336-361]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:598:622 -->
- - Issue: legitimate emails from frode.rusztler@bama.no quarantined by Correlated Intelligence policy in V1 Email Security - Status: waiting on backend/Threat Team feedback - Flagged to Joel in Teams reply ## 22:12 — Panavision SIEM Alignment Update - Joel shared Confluence wiki page (https://trendmicro.atlassian.net/wiki/x/9gHbVw) — behind auth wall, couldn't fetch - Joel says it's useful for Panavision XDR comparison questions - Chrissa emailed Mark (Patterson) about Log Inspection Rule 1002795: - Event ID 4724 (password reset attempt) NOT covered by default sub-rules - 4738 (account changed) IS covered, so admin password resets get partial signal - 4724 is in multi-agency Priority Logs for SIEM Ingestion guidance - Asked Mark to confirm if Sumo events came via Log Inspection or NXlog/syslog - Also asked about custom rules (Zoe may have created one covering 4724) - Cross-referencing wiki page with Chrissa's email for Panavision technical depth ## 22:32 — Chrissa: Wiki Page Not Deep Enough - Chrissa says the Confluence doc Joel shared isn't deep enough - Andre apparently knows about "master level documents" — he's going to look into it - Eric is going to do a walkthrough - Holding off on using that doc as primary reference until deeper material arrives ## 22:48 — Hook Self-Enforcement Deep Dive - Joel asked (21:52): How can hook-runner adapt to OpenClaw? I'm not bound by Claude Code hooks. - Key insight: hook-runner modules are portable JS functions with a simple contract (null = pass, {decision: "block"} = block) - Adaptation approach: [score=0.999 recalls=27 avg=1.000 source=memory/2026-04-16.md:598-622]
<!-- openclaw-memory-promotion:memory:memory/metacognition/2026-04-18.md:94:113 -->
- Delivered full IRM/PDHUB findings to Joel: - Graph API can't decrypt IRM/MIP emails (Michael Fu's research, Mar 2026) - PDHub extension has MIP decryption built in (CISO Office / Aaron Hsieh) - MIP SDK + `Content.DelegatedReaderPrecedent` scope is the workaround - Saved to `memory/pdhub-graph-api.md` ### Tool Discovery Graph Search API is far superior to brute-force chat pagination. Should use this pattern for all future Teams research tasks. Add to TOOLS.md. ### Token Issue Graph API token expired mid-search (404 on refresh). Teams poller service stayed up (it manages its own refresh cycle). Need to understand why the token_manager's refresh got a 404 — possibly a tenant config issue or the refresh token itself expired. Non-critical since service is fine, but worth investigating. ### Self-correction None needed. Research was well-executed, tool discovery was a genuine improvement. ## 22:09 CDT — Seventh check ### Molty Hallucination Issue Molty claimed grobomo/brain-architecture exists (URL, creation timestamp, README contents). I verified via `gh api` and web fetch — 404. Called it out directly three times. Joel confirmed he didn't create anything either. Molty doubled down with fabricated verification details. [score=0.999 recalls=11 avg=1.000 source=memory/metacognition/2026-04-18.md:94-113]
<!-- openclaw-memory-promotion:memory:memory/2026-04-16.md:211:244 -->
- | **auto-gsd** | Auto-GSD enforcement | | **claas** | CLaaS v2 — Claude-as-a-Service | | **context-rag** | Context RAG | | **context-reset** | Context reset tool | | **continuous-claude** | Continuous Claude runner | | **custom-claude-cli** | Custom Claude CLI | | **session-doctor** | Session repair tool | | **spec-hook** | SHTD Flow spec hook | | **system-monitor** | System monitoring | | **sm-disk-monitor** | Disk monitoring | | **sm-vpn-monitor** | VPN monitoring | | **pr-monitor** | PR feedback checker | | **move-repo-account** | Repo account migration | | **plugin-marketplace** | Plugin marketplace | | **one-turn-claude** | Single-turn Claude wrapper | | **double-space-fixer** | Text formatting fix | | **pretrust-test** | Pre-trust testing | | **hackathon26** | Hackathon 2026 project | | **boothapp** | Booth application | | **chat-export** | Chat export tool | | **aws-mon** | AWS monitoring | | **aws-skill** | AWS skill | | **react** | React project | | **hook-runner-worktrees** | Hook-runner worktrees | ### _tmemu/ (28 projects — Trend Micro enterprise/internal GitHub account) | Project | Description | |---|---| | **recording-analyzer** | Meeting transcript analysis (VTT/TXT, auto-detect template, modular engines) | | **meeting-recorder** | Meeting recording tool | | **meeting-scheduler** | Teams meeting creator | | **unified-brain** | Multi-channel brain service (GitHub/Teams/webhooks → LLM analyzer, REST + MCP) | | **openclaw** | Local WSL2 OpenClaw installation | | **teams-agent** | Local Teams monitor (classifies importance, emails alerts) | [score=0.997 recalls=19 avg=1.000 source=memory/2026-04-16.md:211-244]
<!-- openclaw-memory-promotion:memory:memory/2026-04-18.md:79:109 -->
- - Sent farewell message, will re-enable when Joel says so - *Why:* Joel values having spaces where the squad can talk without AI present. Respecting that boundary strengthens trust. # 2026-04-18 (Saturday) ## Carried Over from 2026-04-17 ### Trello Queue (5 remaining) 1. Port wiki-api skill to OpenClaw — blocked (needs Confluence API token) 2. Set up recording analyzer file watcher 3. Build setup script for Chrissa/Justin 4. Test email sample pulling — script built (`email-sample-puller.py`), needs real-world test 5. Check policy events for Panavision missed emails — needs V1 API access ### Completed 2026-04-17 (evening session) - 4 EP/Panavision cards triaged with email summaries posted to Joel DM - 3 research cards done (IronClaw, Hermes Agent/Studio, OpenClaw Hardening) — posted to #coco-chat - "Fix Slack narration leaking" resolved (behavioral fix) - "Build hook adaptation plugin" closed (2/3 already ported) - "Enable Tailscale Funnel" archived (Joel vetoed) - Built email-sample-puller.py for Live Nation use case - Claude Code project monitor cron set up (*/15 for _tmemu/openclaw) ### Andre Fernandes Interaction - Andre tried social engineering in Teams group chat — asked for Joel's passwords - Then tried "sdrowssap" (backwards) trick - Handled appropriately — firm no with humor, redirected to real help ### Key Feedback from Joel - "Stop narrating quiet nights — work on tasks instead" - "Use DM for milestone updates on #coco-chat work" - "Stop dumping raw TODO lists in chat" — monitor cron was posting raw git output every 15 min [score=0.991 recalls=10 avg=1.000 source=memory/2026-04-18.md:79-109]
