# Autonomous Work Loop — Complete Pipeline

> Joel's specification, 2026-04-25. This is the canonical workflow for how
> Coconut processes work from instruction to delivery.

## Pipeline (in order)

```
1. INSTRUCTION RECEIVED
   └── From: user message, self-reflection, or Trello card discovery
   
2. TODO ITEM CREATED
   └── Trello card on appropriate list (Coconut Todo, Joel Todo, etc.)
   └── Card has: title, description, source context
   
3. RESEARCH & DOCUMENT
   └── Web search (SearXNG / web_fetch) for existing solutions
   └── Read current documentation for libraries/APIs involved
   └── Check if someone already built this
   └── Write: research/YYYY-MM-DD-<topic>.md with findings
   └── GATE: research-gate blocks spec writes without this step

4. SPEC OUT PLAN
   └── Write spec/design doc referencing research findings
   └── Include: architecture, implementation plan, edge cases
   └── Update Trello card with spec link

5. PASS TO CLAUDE CODE
   └── Spawn Claude Code worker via sessions_spawn or coding-agent skill
   └── Worker gets: spec, research doc, relevant context
   └── Worker runs in Windows terminal tab (managed by claude-tabs)

6. MONITOR (Opus heartbeat)
   └── trello-work cron (15m) checks Coconut Todo list
   └── claude-tab-monitor cron (30m) checks worker tab health
   └── Workers report status at stop-hook events

7. RECEIVE UPDATES FROM WORKERS
   └── Claude Code stop-hook module instructs workers to update OpenClaw
   └── Workers send: progress, blockers, completion status
   └── OpenClaw processes updates

8. UPDATE & DOCUMENT
   └── Update Trello card (progress, completion, learnings)
   └── Document learnings in memory/daily notes
   └── Create Coconut Lessons card if significant insight
   └── Mark card dueComplete when done → Butler moves to Done

9. UPDATE USER
   └── Notify Joel via appropriate channel (Slack DM, thread)
   └── Only when: completion, blocker, decision needed

10. REPEAT
    └── Pick next highest-priority Trello card
    └── Return to step 3
```

## Gate Enforcement

| Step | Gate | Mode |
|------|------|------|
| 3 → 4 | `research-gate` | Blocks spec writes without research doc |
| 2 | `todo-gate` | Blocks work without active task |
| 5 | `task-tracking-gate` | Ensures task is tracked before execution |
| 9 | `inner-voice` | Blocks wrong-channel messages |

## Research Doc Convention

```
research/
├── 2026-04-25-trello-api.md
├── 2026-04-25-searxng-setup.md
├── 2026-04-26-openclaw-gates.md
└── ...
```

Each doc should contain:
- **Topic & date** — what was researched and when
- **Existing solutions** — what's already out there
- **Current docs** — links to relevant documentation
- **Decision** — build vs. use existing, and why
- **Key findings** — anything that affects implementation

## Audit Logging

Two JSONL log files capture all activity:

| Log | Path | Source | Content |
|-----|------|--------|--------|
| `audit-logger.jsonl` | `~/.openclaw/logs/audit-logger.jsonl` | `claude-code-gates` | Every tool call (pre + post), module pass/block results, timing, commands, file paths. Auto-rotates at 10MB. |
| `openclaw-gates-audit.jsonl` | `~/.openclaw/logs/openclaw-gates-audit.jsonl` | `openclaw-gates` | Gate decisions (todo-gate, research-gate, config-safety, inner-voice), tool calls with sanitized args and result previews. |

Both feed into:
1. **Metacognition cron** — self-audit parses logs for patterns
2. **Joel's monitoring** — grep/jq for workflow analysis
3. **Security forensics** — full trail of all actions

## Key Systems

| System | Role |
|--------|------|
| Trello (To Do List board) | Task queue — single source of truth |
| `trello-work` cron (Opus, 15m) | Pulls and executes cards |
| `claude-tab-monitor` cron (Haiku, 30m) | Monitors Claude Code workers |
| `research-gate` | Enforces research-before-building |
| `claude-code-gates` | Gates on Claude Code worker behavior |
| `openclaw-gates` | Gates on OpenClaw agent behavior |
| `audit-logger.jsonl` | Comprehensive audit log (12K+ entries) |
| `openclaw-gates-audit.jsonl` | Gate-level audit log (1.5K+ entries) |
