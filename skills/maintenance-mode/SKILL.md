---
name: maintenance-mode
description: Enter and exit maintenance mode to silence all polling, crons, services, and external I/O while preserving exact pre-maintenance state for instant restore. Use when the user says "maintenance mode", "quiet mode", "pause everything", "stop all polling", "silence all crons", or needs to stop token burn from background activity to focus on fixing root causes. Also use when exiting maintenance mode or checking maintenance status.
---

# Maintenance Mode

Silence all background activity (polling services, crons, scheduled tasks) with full state preservation. One command in, one command out — state survives session resets.

## Why This Exists

Background polling and cron jobs can burn tokens and cause context resets, creating a vicious cycle: poll → tokens burned → context fills → compaction → lose progress → restart → poll again. Maintenance mode breaks this cycle.

## Usage

### Enter Maintenance Mode
```bash
bash <skill_dir>/scripts/maintenance-mode.sh enter
```
Discovers and stops all active noise sources, saving their state first.

### Exit Maintenance Mode
```bash
bash <skill_dir>/scripts/maintenance-mode.sh exit
```
Restores exact pre-maintenance state — services that were running restart, ones that were stopped stay stopped.

### Check Status
```bash
bash <skill_dir>/scripts/maintenance-mode.sh status
```

## What Gets Discovered and Stopped

The script auto-discovers noise sources rather than hardcoding service names:

1. **Systemd user services** — finds services with polling patterns (names containing `poll`, `monitor`, `bridge`, `sync`, `watch`, `webhook`, `cron`, `schedule`, `timer`). Excludes the OpenClaw gateway itself.
2. **OpenClaw crons** — lists all enabled cron jobs via `openclaw cron list` and disables them.
3. **Linux crontab** — backs up and clears the user's crontab.
4. **Active network connections** — scans for processes making repeated outbound HTTP/HTTPS connections (curl, python, node polling loops). Reports them for manual review.

## State Preservation

All state is saved to `~/.openclaw/maintenance-state/` before anything is touched:
- `crontab.bak` — full crontab
- `systemd-services.json` — which services were active/enabled
- `openclaw-crons.json` — which OpenClaw crons were enabled (with IDs for restore)
- `network-scan.txt` — snapshot of outbound connections at time of entry
- `entered-at.txt` — timestamp

On exit, state directory is archived (not deleted) as `maintenance-state.last-<timestamp>`.

## Flag File

Creates `MAINTENANCE_MODE.md` in the workspace root. Heartbeat and cron handlers should check for this file and skip external work when it exists.

## Adapting to Any Environment

The skill does NOT hardcode service names. It pattern-matches to find polling services, so it works on any OpenClaw installation regardless of what custom services the user has set up. The discovery patterns:

- Systemd: `poll|monitor|bridge|sync|watch|webhook|cron|schedule|timer|fetch|scrape`
- Processes: repeated outbound connections on ports 80/443/8080/8443
- OpenClaw: `openclaw cron list` (captures whatever crons exist)
- Crontab: `crontab -l` (captures whatever's scheduled)
