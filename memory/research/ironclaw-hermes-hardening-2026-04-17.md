# Research: IronClaw, Hermes Agent, Hermes Studio, OpenClaw Hardening
_Completed: 2026-04-17 ~21:40 CDT_

## IronClaw (nearai/ironclaw)
**What:** Rust reimplementation of OpenClaw, focused on privacy/security. Built by NEAR AI.
**Status:** Active development (staging branch)

### Key Differences from OpenClaw
| Aspect | OpenClaw | IronClaw |
|--------|----------|----------|
| Language | TypeScript/Node | Rust |
| Sandbox | Docker | WASM (WebAssembly) |
| Database | SQLite | PostgreSQL + pgvector |
| Distribution | npm package | Single binary |

### Security Architecture (Strong)
- WASM sandbox with capability-based permissions
- Credential injection at host boundary — secrets never exposed to tool code
- Leak detection scanning requests/responses for exfiltration
- Endpoint allowlisting (HTTP only to approved hosts)
- Prompt injection defense (pattern detection, sanitization, policy enforcement)
- AES-256-GCM encryption for stored secrets

### Features
- Multi-channel: REPL, HTTP webhooks, WASM channels, web gateway
- Docker sandbox option (orchestrator/worker pattern)
- Routines engine (cron, event triggers, webhooks)
- Heartbeat system, parallel jobs, self-repair
- Dynamic tool building (describe → WASM tool)
- MCP protocol support
- Hybrid search (full-text + vector, RRF)

### Requirements
- Rust 1.85+, PostgreSQL 15+ with pgvector, NEAR AI account
- Available via brew, shell installer, cargo build

### Pros for Us
- Security-first design is excellent — WASM sandbox is lighter than Docker
- Credential protection model is superior to OpenClaw's
- Single binary deployment is simpler
- PostgreSQL with pgvector means better search capabilities

### Cons / Risks
- Requires PostgreSQL (heavier infra than SQLite)
- NEAR AI account required for auth (vendor dependency)
- Rust = harder to extend/customize vs TypeScript
- Feature parity tracking doc exists but unclear how complete
- Smaller community than OpenClaw
- No native Teams/email channel yet (OpenClaw has more channel plugins)

### Weaknesses/Vulns to Watch
- NEAR AI auth dependency — single point of failure
- pgvector extension needs separate install/management
- WASM sandbox security depends on wasmtime runtime — track CVEs
- No mention of rate limiting on gateway endpoints

---

## Hermes Agent (NousResearch/hermes-agent)
**What:** Self-improving AI agent by Nous Research. Python-based. Has learning loop.
**Status:** Active, v0.9.0+

### Key Features
- **Learning loop:** Creates skills from experience, self-improves during use
- **Memory:** Persistent with periodic nudges, FTS5 session search, Honcho user modeling
- **Multi-platform:** Telegram, Discord, Slack, WhatsApp, Signal, CLI
- **Terminal backends:** Local, Docker, SSH, Daytona, Singularity, Modal (serverless)
- **Cron scheduler** with delivery to any platform
- **Subagent spawning** for parallel workstreams
- **OpenClaw migration built-in** (`hermes claw migrate`)
- **Skills:** Compatible with agentskills.io standard
- **RL Training:** Tinker-Atropos integration for trajectory generation

### Architecture
- Python (uv-based), requires Python 3.11+
- File-based memory (MEMORY.md, USER.md, SOUL.md — same pattern as OpenClaw)
- Config via YAML (~/.hermes/config.yaml)

### Comparison to OpenClaw
| Aspect | OpenClaw | Hermes |
|--------|----------|--------|
| Language | TypeScript | Python |
| Learning | Skills via manual creation | Auto-creates and self-improves skills |
| Memory | MEMORY.md + daily notes | MEMORY.md + Honcho user modeling + session search |
| Sandbox | Docker | Multiple backends (Docker, SSH, Modal, etc.) |
| Channels | Many native plugins | Gateway-based (Telegram, Discord, etc.) |
| RL Training | No | Yes (Atropos) |
| Migration | N/A | Can import from OpenClaw |

### Pros
- Self-improving skills is genuinely innovative
- Multiple terminal backends (serverless Modal is interesting)
- OpenClaw migration path exists
- Active community (Nous Research Discord)

### Cons / Risks
- Python = different ecosystem from our TypeScript tooling
- Switching would mean rebuilding all our custom integrations
- Nous Research focus on their own models/portal
- Less mature channel support than OpenClaw

---

## Hermes Studio (JPeetz/Hermes-Studio)
**What:** Full-featured web UI for Hermes Agent. Fork of hermes-workspace, heavily extended.
**Author:** Joerg Peetz (Senior TSE, OpenClaw early adopter)

### Standout Features
- **Cron Job Manager** — the only Hermes UI with built-in scheduler (create/edit/pause/trigger/monitor)
- **Multi-Agent Crews** — named groups of specialized agents, parallel dispatch, live SSE feeds
- **Visual Workflow Builder** — DAG editor for task pipelines
- **Interactive Knowledge Graph** — force-directed memory visualization
- **Execution Approvals UI** — approve/deny/always-allow from browser
- **Skill Installation** from skillsmp.com registry
- **Cost Tracking** — per-agent token usage and estimated API costs
- **MCP Server Management** from UI
- **Agent Library** — custom agents with system prompts, model overrides
- **Audit Trail** — chronological timeline of all tool calls
- **Systemd auto-start** from UI
- **8 themes, mobile PWA, Redis session persistence**

### Relevance
- This is the kind of management UI we don't have for OpenClaw
- Crew templates and multi-agent orchestration could be useful patterns
- The cron/job management UI approach is polished

---

## OpenClaw Security Hardening (JPeetz/OpenClaw_Security_Hardening)
**What:** Battle-tested security configs, firewall scripts, audit checklists for OpenClaw.
**Author:** Same Joerg Peetz

### Contents
- `templates/openclaw-hardened.jsonc` — full hardened baseline config
- `templates/multi-agent.jsonc` — multi-agent isolation
- `templates/sandbox.jsonc` — sandbox config
- Channel-specific secure configs (WhatsApp, Discord, Telegram)
- `scripts/firewall-docker.sh` — Docker/UFW firewall rules
- `scripts/monthly-audit.sh` — automated audit
- `scripts/generate-token.sh` — secure token generation
- `docs/THREAT-MODEL.md` — threat model overview
- `SECURITY-CHECKLIST.md` — printable monthly audit checklist

### Key Principles
1. Gateway bound to localhost with token auth
2. Per-sender session isolation
3. Messaging-only tool profile with explicit deny lists
4. Filesystem restricted to workspace only
5. Exec completely disabled by default
6. All channels locked to allowlist/pairing

### Action Items for Us
- **Run `openclaw security audit --deep`** on our instance
- Review our config against the hardened baseline
- Consider the firewall-docker.sh script (we're on WSL, may need adaptation)
- The monthly audit script could be a cron job
- 135,000 exposed instances on public internet is a real stat — we should verify we're not one of them

### Tested With
- OpenClaw v2026.3.8+ (we should check our version)
- Node.js 22.12.0+
- Ubuntu 24.04 LTS

---

## Summary & Recommendations

1. **IronClaw:** Interesting security model but not ready to replace OpenClaw for us. WASM sandbox and credential injection are great ideas. Worth watching. The PostgreSQL + NEAR AI requirements add complexity we don't need. **Don't deploy to AWS yet — wait for more maturity.**

2. **Hermes Agent:** Strong competitor to OpenClaw with innovative self-improving skills. The migration path from OpenClaw is notable. Not worth switching — we're heavily invested in OpenClaw's ecosystem and our custom integrations. **Good to know it exists as a fallback.**

3. **Hermes Studio:** Impressive UI work. We could learn from the crew/workflow patterns. Not directly useful unless we switch to Hermes.

4. **OpenClaw Hardening:** **Immediately actionable.** We should clone this repo, compare our config against the hardened baseline, and run the security audit. This is the highest-value item from this research batch.
