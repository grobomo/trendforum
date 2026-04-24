# 🔧 MAINTENANCE MODE

**Status:** ACTIVE
**Since:** 2026-04-23 19:31 CDT
**Requested by:** Joel

## Why This Exists
Teams polling (`teams-poller.service` at 3s intervals) burns ~25K API calls/day, causing:
- Massive token costs (~$10K/month contributor)
- Frequent context resets from bloated sessions
- Context resets override in-progress work, creating a vicious cycle:
  poll → tokens burned → context fills → compaction → lose progress → restart → poll again

Maintenance mode breaks this cycle by shutting off all external noise so we can fix the root cause (migrate to webhooks) without the polling constantly eating our runway.

## What's Off
- All cron jobs (backed up to `.crontab-backup-maintenance.txt` for instant restore)
- All external inputs: Teams, email, GitHub, Trello polling
- All external outputs: no posts to Teams, no Slack channel responses
- Heartbeat external checks (email, calendar, weather, Teams gaps)

## What's On
- Slack DM with Joel (only active channel)
- Any work — coding, specs, git, launching Claude Code workers, etc.
- This is a "quiet room" mode, not a freeze

## How to Resume
1. Joel says to exit maintenance mode
2. Restore crons: `crontab /home/ubu/.openclaw/workspace/.crontab-backup-maintenance.txt`
3. Delete this file
4. Verify services: `systemctl --user status teams-poller webhook-server`

## Cron Backup Location
`/home/ubu/.openclaw/workspace/.crontab-backup-maintenance.txt`
Full crontab preserved exactly as it was — one command restores everything.
