# HEARTBEAT.md

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

## Trello Board Review — MANDATORY WORK
- Check Coconut Todo list for new/updated cards
- Review all lists for accuracy
- *DO THE WORK.* Pick the highest priority open card and execute it. Do not reply HEARTBEAT_OK while cards remain.
- Priority order: [URGENT] > [Due today/tomorrow] > [P1] > [P2] > [P3] > everything else
- Board: TyFBN1Bx | API key/token in keyring (openclaw/TRELLO_API_KEY, openclaw/TRELLO_TOKEN)
- Mark cards dueComplete=true when done (automation moves to Done list)
- If a task requires Joel's input/approval, skip it and do the next one. Don't use "waiting on Joel" as an excuse to idle.
