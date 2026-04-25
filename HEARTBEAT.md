# HEARTBEAT.md

## Autonomous Operation Cycle (every 15 min via cron)

This is your work loop. The cron fires every 15 min as a system event. When it fires, WORK — don't review.

### 1. Slack Scan
- Run: `python3 scripts/slack-poller/state_manager.py check`
- If due: scan each channel using `message(action=read, channel=slack, target=<channel_id>, limit=10)`
- Respond to unresponded human messages (ignore bot IDs: U0ATFQQ4WNS, U0AURHRR4M6)
- After scanning: `python3 scripts/slack-poller/state_manager.py done`

### 2. Trello Work — MANDATORY
- Pull Coconut Todo list for open cards
- Pick highest priority and DO THE WORK
- Priority: [URGENT] > [Due today/tomorrow] > [P1] > [P2] > [P3] > everything else
- Mark cards dueComplete=true when done (automation moves to Done)
- If a task requires Joel's input, skip it and do the next one
- Do NOT reply HEARTBEAT_OK while cards remain

### 3. Claude Code Tab Monitor
- Run: `python3 scripts/claude-tabs/manage.py monitor`
- 🔴 DEAD: check transcript, verify + close if done
- 🟡 STALE: investigate stuck process
- ⚠️ NO CHECKIN: check stop hook

### 4. Metacognition (brief)
- Quick self-review: 2-3 sentences max
- Am I repeating mistakes? Violating lessons?
- Append to `memory/metacognition/YYYY-MM-DD.md`
- Post to #coco-metacognition (C0ATCRVSB71) ONLY if catching a real mistake

### 5. Schedule Briefing (hourly)
- Data source: `/tmp/schedule-briefing-latest.json` (gathered by cron)
- If fresh + unposted: synthesize and post to #scheduling (C0ATK8YJQD9)
- Check `/tmp/schedule-briefing-last-posted.txt` to avoid dupes

### 6. Continue
- If time remains, work on the next Trello card
- Never idle while cards exist
- Report what you DID, not what you COULD do

## Teams Monitoring — SUSPENDED
- *Paused by Joel (2026-04-24).* Do NOT poll, respond to, or check Teams.

## Rules
- **NEVER ask "should I continue?" — the answer is always yes**
- **NEVER reply HEARTBEAT_OK if open tasks exist**
- Only pause for: external customer emails, public posts, infra deletion, spending money
- Everything else: just do it
