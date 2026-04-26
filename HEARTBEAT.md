# HEARTBEAT.md

## Architecture: Delegated Cron Model (2026-04-25)

The autonomous work loop is split across model-appropriate crons. No single monolith.

### Model Hierarchy
- **Haiku** — mechanical tasks only (scan, run scripts, report numbers, flag things). Never responds to humans.
- **Sonnet** — semantic analysis (triage missed messages, self-reflection, urgency assessment).
- **Opus** — reasoning + actual work (respond to humans, execute Trello tasks, deep thinking).

### Active Crons

| Job | Model | Interval | Purpose |
|-----|-------|----------|---------|
| slack-missed-detector | Haiku | 15m | Scan channels, flag unreplied messages, alert Joel DM |
| trello-work | Opus | 30m | Pull + execute Coconut Todo cards |
| session-health | Haiku | 30m | Run monitor.py, alert if CRITICAL |
| claude-tab-monitor | Haiku | 30m | Run manage-claude-code.py monitor, alert if DEAD/STALE |
| metacog-orchestrator | Sonnet | 1h | Run all metacog modules, detect trends, create tasks, post actionable findings |
| schedule-briefing | Haiku | 1h | Post schedule data to #scheduling if fresh |

### Pre-existing Crons (unchanged)
| Job | Model | Schedule | Purpose |
|-----|-------|----------|---------|
| Memory Dreaming | default | 3 AM daily | Memory consolidation |
| daily-squad-scheduler | default | 7 AM weekdays | Squad schedule gathering |

### Rules
- Haiku NEVER responds to humans — detect and flag only
- Opus handles all human-facing responses and complex task execution
- Sonnet bridges the gap — semantic understanding without full reasoning cost
- All isolated sessions, light context
- 🌴 bookends on any outbound messages

### Teams Monitoring — SUSPENDED
- Paused by Joel (2026-04-24). Do NOT poll, respond to, or check Teams.
