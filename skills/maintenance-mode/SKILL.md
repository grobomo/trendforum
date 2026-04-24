---
name: maintenance-mode
description: Enter and exit maintenance mode to silence all polling, crons, services, and external I/O while preserving exact pre-maintenance state for instant restore. Use when the user says "maintenance mode", "quiet mode", "pause everything", "stop all polling", "silence all crons", or needs to stop token burn from background activity to focus on fixing root causes. Also use when exiting maintenance mode or checking maintenance status.
---

# Maintenance Mode

Silence all background noise (polling services, crons, scheduled tasks, network pollers) with full state preservation. One command in, one command out — state survives session resets.

## Why This Exists

Background polling and cron jobs burn tokens and cause context resets, creating a vicious cycle: poll → tokens → context fills → compaction → lose progress → restart → poll again. Maintenance mode breaks this cycle by silencing everything so root causes can be fixed without interference.

## Enter Maintenance Mode

### Step 1: Discover Noise Sources

Gather raw system state. Do NOT filter yet — collect everything and analyze semantically.

```bash
# All active user services (names + descriptions)
systemctl --user list-units --type=service --state=active --no-pager

# All OpenClaw crons
openclaw cron list 2>/dev/null

# Current Linux crontab
crontab -l 2>/dev/null

# Active outbound network connections with owning processes
ss -tnp 2>/dev/null | grep -E 'ESTAB' | head -40

# Running processes that might be polling loops
ps aux | grep -vE 'grep|systemd|dbus|openclaw-gateway' | head -40
```

### Step 2: Classify Each Source

For each discovered item, determine: **is this a noise source or essential infrastructure?**

Noise sources (STOP these):
- Services that poll external APIs on intervals (Teams, email, GitHub, Trello, calendar, etc.)
- Cron jobs that trigger external API calls or wake the agent for routine checks
- Processes running polling loops (curl in a while loop, python scripts with `sleep()` + API calls)
- Webhook subscription renewals (stop if the webhook server itself is stopped)
- Monitoring/sync services that generate inbound messages to the agent

Essential infrastructure (NEVER stop):
- `openclaw-gateway` — the agent's communication backbone (stopping this kills all channels including DM)
- The agent's own process
- System services (dbus, systemd internals, SSH, etc.)
- Services the user explicitly asks to keep running

Gray area (ASK the user):
- Webhook servers that receive but don't poll (low cost but may not be needed)
- Services you're unsure about

### Step 3: Save State Before Touching Anything

Run the backup script. This snapshots the exact pre-maintenance state so exit restores it perfectly.

```bash
bash <skill_dir>/scripts/maintenance-mode.sh save
```

This saves to `~/.openclaw/maintenance-state/`:
- `crontab.bak` — full crontab
- `systemd-services.json` — pass the list of services to stop (see below)
- `openclaw-crons.json` — cron IDs and names
- `entered-at.txt` — timestamp

For systemd services, write the JSON yourself based on your semantic analysis:
```bash
cat > ~/.openclaw/maintenance-state/systemd-services.json << 'EOF'
{
  "service-name": {"active": "active", "enabled": "enabled"},
  ...only services you classified as noise...
}
EOF
```

### Step 4: Stop Everything

```bash
bash <skill_dir>/scripts/maintenance-mode.sh stop
```

This stops discovered services, disables OpenClaw crons, and clears crontab. It reads the service list from `systemd-services.json` — so only services you classified as noise get stopped.

### Step 5: Write Flag File

Create `MAINTENANCE_MODE.md` in workspace root documenting what was stopped and why.

## Exit Maintenance Mode

```bash
bash <skill_dir>/scripts/maintenance-mode.sh exit
```

Restores exact pre-maintenance state: services that were running restart, services that were stopped stay stopped, crontab and OpenClaw crons re-enabled. State directory is archived (never deleted).

## Check Status

```bash
bash <skill_dir>/scripts/maintenance-mode.sh status
```
