# Hermes Slack Integration — Setup Progress

## Slack App Created ✅ (2026-04-19)
- **App Name:** Hermes
- **App ID:** A0AUA5YJZ3K
- **Client ID:** 10932117323893.10962202645121
- **Workspace:** Misfits (T0ATE3F9HS9)
- **Created via:** App manifest (JSON)

## Tokens Stored ✅
All in Linux keyring under `openclaw/` prefix:
- `HERMES_SLACK_APP_TOKEN` — xapp-1-... (connections:write scope, for Socket Mode)
- `HERMES_SLACK_BOT_TOKEN` — xoxb-... (bot OAuth token)
- `HERMES_SLACK_SIGNING_SECRET` — signing secret for request verification

## Configuration ✅
- **Socket Mode:** Enabled
- **Events API:** Enabled
- **Bot Events:** app_mention, message.channels, message.groups, message.im, message.mpim
- **Bot Scopes:** app_mentions:read, channels:history, channels:read, chat:write, groups:history, groups:read, im:history, im:read, mpim:history, users:read, reactions:read, reactions:write

## Hermes Bot Identity
- **Bot username:** hermes
- **Bot user ID:** U0AURHRR4M6
- **Bot ID:** B0ATFRVFT0X
- **Workspace:** Misfits (T0ATE3F9HS9)

## Gateway Status ✅
- slack-bolt 1.28.0 + slack-sdk 3.41.0 installed in Hermes venv
- Gateway running via systemd (hermes-gateway.service)
- Slack Socket Mode connected
- Home channel: #all-misfits (C0ATFDQRGRL)

## Next Steps
1. ~~Configure Hermes gateway with Slack tokens~~ ✅
2. ~~Start/restart Hermes gateway with Slack platform enabled~~ ✅
3. Test message sending/receiving
4. Invite Hermes bot to #all-misfits, #coco-chat

## Config Locations
- Platform module: `~/.hermes/hermes-agent/gateway/platforms/slack.py`
- Config: `~/.hermes/config.yaml` (slack section exists, needs tokens)
- Docs: `~/.hermes/hermes-agent/website/docs/user-guide/messaging/slack.md`

## Hermes Gateway Status
- Running on port 8642, ~58 MB RAM
- Slack platform module exists but needs token configuration
