# DECISIONS.md — Active Decisions (Read Every Session)

This file is injected into every session context. If you're about to do something that contradicts a decision here, STOP and read it first.

## Architecture Decisions

### Teams Channel — USE NATIVE PLUGIN, NOT SCRIPTS
- **Decision:** Set up `@openclaw/msteams` native plugin (like Slack)
- **Why:** `poll_all.py` was called 21,749 times in one day, consuming ~100M+ tokens. It misses messages, triple-replies, and loses decisions between compactions.
- **Status:** BLOCKED — needs Azure Bot registration (Joel's approval)
- **Interim:** `send_direct.py` for outbound, `check_gaps.py` for inbound detection
- **DO NOT:** Build more polling scripts, custom webhook servers, or patch poll_all.py further
- **See:** TEAMS-ARCHITECTURE.md for full details

### Token Optimization — REDUCE POLL FREQUENCY
- **Decision:** Reduce cron poll frequency from 3min to longer intervals
- **Why:** 21,749 polls × ~5K tokens = ~100M tokens/day wasted on empty polls
- **Status:** DONE — 5-min rate limiter added to poll_all.py (2026-04-22 23:50 CDT)
- Webhook watchdog.py cron REMOVED (was running every minute, 1440x/day)
- **DO NOT:** Remove the rate limiter or re-add watchdog cron

### Message Styles — DOCUMENTED AND LOCKED
- **Decision:** Island style = default, Clean style = available, Plain = fallback
- **Why:** Joel approved island ("Amazing 😍😍😍"), approved clean ("clean af")
- **Status:** DONE — templates in `scripts/teams-poller/styles/STYLES.md`
- **DO NOT:** Redesign styles or hunt through chat history for the format

### Memory Continuity — WRITE DECISIONS, NOT JUST NOTES
- **Decision:** All architectural decisions go in THIS file, not just daily notes
- **Why:** 493 compactions in one day = 493 amnesia events. Daily notes get compacted away.
- **Status:** ACTIVE
- **DO NOT:** Make architectural decisions without recording them here

### Dole Account — COSTA RICA TIME
- **Decision:** All Dole meetings scheduled in Costa Rica time (CST, UTC-6)
- **Why:** Most Dole admins are in Costa Rica
- **Status:** ACTIVE

## Anti-Patterns (Don't Repeat)

- **Circular rebuild:** Don't rebuild Teams infrastructure that was already abandoned. Check this file first.
- **Verify by proxy:** Don't check logs as proof. Read back from the target system (Graph API, etc.)
- **Permission-seeking:** Act on reversible decisions. Ask only for irreversible ones.
- **Stats over work:** Don't build dashboards. Do the actual work.
- **Triple-reply:** Don't compose a reply to a message you already replied to. Check tracker first.
