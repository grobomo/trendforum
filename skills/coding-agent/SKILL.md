---
name: coding-agent
description: 'Manage Claude Code tabs on Windows via manage-claude-code.py. Use when: (1) launching new CC work sessions for coding tasks, (2) monitoring active tabs for stalls/crashes, (3) verifying and closing completed work, (4) parallel task execution (max 3 tabs). NOT for: simple one-liner fixes (just edit), reading code (use read tool), or any work in ~/clawd workspace.'
metadata:
  openclaw:
    emoji: "🖥️"
---

# Claude Code Tab Manager

Custom system for managing parallel Claude Code sessions on Windows. All coding tasks (gates, scripts, plugins, multi-file changes) MUST go through CC tabs — not main session edits.

## Architecture

- **Manager script:** `scripts/claude-tabs/manage-claude-code.py` (workspace-relative)
- **Tracker state:** `scripts/claude-tabs/tracker.json`
- **Launcher:** Uses Joel's `context-reset/new_session.py` via Windows Python to open Windows Terminal tabs
- **Trello integration:** Cards auto-created in "Claude Code Tabs" list for visibility
- **Cron monitor:** `claude-tab-monitor` runs every 30 min (Haiku) — detects DEAD/STALE tabs

## Hard Constraints

- **Max 3 simultaneous tabs** — Windows memory/CPU limit (Joel, 2026-04-26)
- **Check `status` before launching** — never exceed the cap
- **Coding tasks go through CC** — building this gate to enforce CC usage without using CC was the mistake that prompted this skill rewrite

## Commands

### Launch a new tab
```bash
python3 scripts/claude-tabs/manage-claude-code.py launch \
  --project /path/to/project \
  --task "Build the feature" \
  --task-id T001 \
  --prompt "Optional custom prompt"
```
- Creates Trello card in CC Tabs list
- Opens Windows Terminal tab via new_session.py
- Records in tracker.json

### Check status of active tabs
```bash
python3 scripts/claude-tabs/manage-claude-code.py status
```
- Shows 🟢 Active / 🟡 STALE (>15m no activity) / 🔴 DEAD (process gone)
- Reports transcript line count, last checkin, context resets

### Monitor for issues (used by cron)
```bash
python3 scripts/claude-tabs/manage-claude-code.py monitor
```
- Outputs `CLAUDE_TAB_ISSUES` if problems found, else "All tabs healthy"
- Checks: process alive, transcript freshness, checkin recency

### Record a checkin (from CC session updates)
```bash
python3 scripts/claude-tabs/manage-claude-code.py checkin \
  --project "project-name" \
  --checkin-status progress \
  --detail "Built classify.py, starting tests"
```
- Status values: `done`, `blocked`, `progress`, `tests`, `error`
- Adds Trello comment for visibility

### Verify work is complete
```bash
python3 scripts/claude-tabs/manage-claude-code.py verify --tab-id tab-XXXXXXX
```
- Checks: process still running?, TODO.md items, recent git commits
- Use BEFORE closing — depth over checkboxes!

### Close a completed tab
```bash
python3 scripts/claude-tabs/manage-claude-code.py close \
  --tab-id tab-XXXXXXX \
  --summary "Built and tested classify.py with 4-class output"
```
- Kills process if still running
- Updates Trello card (dueComplete)
- Records completion in tracker

### List all tabs
```bash
python3 scripts/claude-tabs/manage-claude-code.py list
```

## Workflow: Parallel Task Execution

1. Check current tab count: `manage-claude-code.py status`
2. If < 3 active, pull top Trello card from Coconut Todo
3. Launch CC tab with task details
4. Repeat until 3 tabs running
5. Monitor via cron (every 30m) — stale/dead tabs get flagged
6. When a tab reports done: `verify` → `close` → backfill next card

## Key Principle

Every task launched through this system must be:
- **Purposeful** — understand WHY before launching
- **Verified** — run `verify` and check the actual output works
- **Tested** — if it's a gate/script/plugin, prove it enforces/runs correctly
- **Closed with evidence** — summary must say what was built AND that it was tested

A file that exists but doesn't work is not done.

## Trello Integration

- Cards created in list `69ebe51d36d2269f7c93de8c` (Claude Code Tabs)
- Board: To Do List (`TyFBN1Bx`)
- Checkins add comments to the card
- Close sets `dueComplete: true` (triggers Trello automation → Done)
- Creds from keyring: `openclaw/TRELLO_API_KEY`, `openclaw/TRELLO_TOKEN`

## Path Notes

- Windows Python: `C:\Users\joelg\AppData\Local\Programs\Python\Python312\python.exe`
- new_session.py: `C:\Users\joelg\Documents\ProjectsCL1\_grobomo\context-reset\new_session.py`
- WSL paths starting with `/mnt/c/` get converted to Windows format automatically
- WSL paths starting with `/home/` convert to `\\wsl$\Ubuntu\...`
