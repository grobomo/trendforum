# PURGED: poll-all cron job

**Purged:** 2026-04-23 20:12 CDT
**Joel's instruction:** "Stop the polling immediately" → "Purge it from your memory (archive a note about why it must be purged)"

## What it was
- OpenClaw cron job `poll-all` (id: `7c9b756d-9a80-4b19-8395-cb7d1fb95388`)
- Ran every 180 seconds (3 minutes)
- Executed `poll_all.py` which checked Teams, GitHub, Email, Trello, and watchdog status
- Also had a system crontab entry (removed)

## Why it was purged
1. **Token burn:** ~14,431 daily API calls consuming massive session context
2. **Reactive loop:** Every 3 min interrupt prevented any proactive/building work
3. **Context resets:** Large session sizes from poll output caused gateway crashes and compaction loops
4. **Vicious cycle:** Poll → tokens → context reset → lose progress → restart project from scratch
5. **Never built anything:** 2.5 hours of polling produced ~15 Teams replies but zero progress on actual tasks (hook modules, Tibor research, Andre EC2, etc.)

## What replaced it
- Teams: moving to webhooks (teams-webhooks project)
- Maintenance mode concept: shut off all crons except Slack DM
- Joel wants Coconut to be project manager, not reactive poll processor

## Never restore this
The polling approach is fundamentally wrong. Build webhooks instead.
