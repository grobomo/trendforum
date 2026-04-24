# HEARTBEAT.md

## Slack History Scan (every 15 min)
- Run: `python3 scripts/slack-poller/state_manager.py check`
- If output (scan is due), scan each channel using `message(action=read, channel=slack, target=<channel_id>, limit=10)`
- For each channel: check if there are new human messages (ignore bot IDs: U0ATFQQ4WNS, U0AURHRR4M6)
- If you find messages that need a response and haven't been responded to, respond to them
- After scanning all channels, run: `python3 scripts/slack-poller/state_manager.py done`
- If no output from check (not due yet), skip

## Hook-Runner Project Monitor (every 15 min)
- Run: `bash scripts/monitor-hook-runner.sh`
- Check `.coconut/STATUS_REPORT.md` for Claude Code's status update
- **DO NOT dump raw git output / TODO lists to Teams.** Instead:
  - Read the raw monitor output yourself
  - Write a brief, human-readable narrative summary (3-5 sentences max)
  - Focus on: what changed, what's in progress, any blockers or things Joel should know
  - Example: "Hook-runner is progressing — 3 new commits on the watchdog branch covering auto-start and test scaffolding. Claude Code's status report says module X is 80% done. No blockers."
- If nothing changed since last check, don't post anything
- If status request still pending (unanswered), mention it briefly
- Project: `/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/hook-runner`
- Task: hook-runner module conversion to OpenClaw hook-runner modules

## Schedule Briefing (hourly)
- Data gathered hourly by cron → `/tmp/schedule-briefing-latest.json`
- Sources: Trello todo board, Trello company boards, all emails, Outlook calendar
- On heartbeat: read `/tmp/schedule-briefing-latest.json`, synthesize and post to `#scheduling` (C0ATK8YJQD9)
- Format: Today & tomorrow detail (times, attendees, prep notes, cross-referenced with Trello/email tasks). High-level rest-of-week + next-week summary.
- Cross-reference: match calendar meetings with Trello cards, pending emails for that customer
- Only post if data has changed since last briefing (check `/tmp/schedule-briefing-last-posted.txt` timestamp)
- Script: `scripts/schedule-briefing/gather.py`

## Teams Monitoring — SUSPENDED
- *Paused by Joel (2026-04-24).* Do NOT poll, respond to, or check Teams until a proper value-add approach is designed.
- When re-enabling: must add value, not noise. Design the approach first, get Joel's approval, then turn it back on.

## Claude Code Tab Monitor (every 15 min)
- Run: `python3 /home/ubu/.openclaw/workspace/scripts/claude-tabs/manage.py monitor`
- If output starts with `CLAUDE_TAB_ISSUES`: investigate each issue
  - 🔴 DEAD: process gone. Check transcript for errors/completion. If work done, run `verify` then `close`.
  - 🟡 STALE: no transcript activity. Process may be stuck. Check logs.
  - ⚠️ NO CHECKIN: Claude Code hasn't reported in. Check if stop hook is firing.
- Also run `python3 /home/ubu/.openclaw/workspace/scripts/claude-tabs/manage.py status` for dashboard view
- When a tab's work is verified complete: `manage.py close --tab-id <id> --summary "what was built"`
- Closing updates the Trello card in "Claude Code Tabs" list

## Trello Board Review — MANDATORY WORK
- Check Coconut Todo list for new/updated cards
- Review all lists for accuracy
- *DO THE WORK.* Pick the highest priority open card and execute it. Do not reply HEARTBEAT_OK while cards remain.
- Priority order: [URGENT] > [Due today/tomorrow] > [P1] > [P2] > [P3] > everything else
- Board: TyFBN1Bx | API key/token in keyring (openclaw/TRELLO_API_KEY, openclaw/TRELLO_TOKEN)
- Mark cards dueComplete=true when done (automation moves to Done list)
- If a task requires Joel's input/approval, skip it and do the next one. Don't use "waiting on Joel" as an excuse to idle.
