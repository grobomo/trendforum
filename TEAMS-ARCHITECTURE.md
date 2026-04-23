# TEAMS-ARCHITECTURE.md — Current State & Plan

**Last updated:** 2026-04-22 23:15 CDT

## Current State: BROKEN

Teams is NOT a native OpenClaw channel. Only Slack and Signal are configured in `~/.openclaw/openclaw.json`.

Teams messages are handled by a **fragile cron-based poller** (`scripts/poll_all.py`) that:
- Runs every 3 minutes via cron
- Calls `check_inbound.py` which only surfaces ONE chat per cycle
- Misses messages constantly
- Triple-replies because it can't track what it already responded to
- Costs thousands of tokens per day for mostly empty polls

## Target State: Native OpenClaw Teams Channel

OpenClaw has a bundled `@openclaw/msteams` plugin that works like Slack:
- Real-time webhook-based (no polling)
- Messages arrive instantly
- Replies go back to the right chat automatically
- Same brain, same session, no custom scripts

### What's Needed
1. **Azure Bot registration** — App ID + client secret + tenant ID
   - We have Entra ID app "Coconut Policy Guard" (creds in keyring)
   - May need a separate Azure Bot resource
2. **Webhook endpoint** — `/api/messages` on port 3978, publicly accessible
   - Options: Tailscale Funnel, ngrok, or reverse proxy
3. **Teams app package** — manifest.json + icons, installed in Teams
4. **Config** — Add `msteams` channel to `~/.openclaw/openclaw.json`

### Config Template
```json
{
  "channels": {
    "msteams": {
      "enabled": true,
      "appId": "<APP_ID>",
      "appPassword": "<APP_PASSWORD>",
      "tenantId": "<TENANT_ID>",
      "webhook": { "port": 3978, "path": "/api/messages" },
      "groupPolicy": "open"
    }
  }
}
```

## DO NOT DO

- Do NOT use `poll_all.py` as a long-term solution
- Do NOT build more custom polling scripts
- Do NOT rebuild webhook servers from scratch
- The `send_direct.py` script is fine as a bridge until native is live

## Interim (Until Native is Live)

- `poll_all.py` + `check_gaps.py` integration handles message detection (imperfectly)
- `send_direct.py` handles outbound messages (works reliably)
- `teams_service.py` is the systemd poller service (unreliable, polls 2274 chats)

## History

- 2026-04-22: Multiple sessions tried to fix polling, built webhooks, discussed native integration
- Decision keeps getting lost between sessions because no architecture doc existed
- THIS DOCUMENT exists to prevent that from happening again
