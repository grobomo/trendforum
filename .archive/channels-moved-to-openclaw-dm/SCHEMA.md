# Channel State Schema

## What Is a "Conversation"?

A **conversation** is any sustained thread of communication, regardless of platform or method. This includes:

- **Slack channels** — group or DM
- **Teams chats** — 1:1, group, or team channels
- **Email threads** — identified by subject/thread-id
- **Trello boards** — each board is a conversation context
- **GitHub repos/issues/discussions** — each repo or thread
- **Any future comm source** — Signal, WhatsApp, Telegram, etc.

> "A conversation is any thread of communication no matter the comm method or source." — Joel, 2026-04-24

## YAML Schema

Every conversation gets a state file in `channels/` following this schema:

```yaml
# Required fields
channel_id: string         # Platform-specific identifier
platform: string           # slack | teams | email | trello | github | ...
type: string               # dm | group | channel | board | repo | thread
name: string               # Human-readable name
purpose: string            # What this conversation is for

# Tracking
last_scanned: datetime     # ISO 8601, UTC
last_human_message_ts: string|null  # Platform-native timestamp
last_human_message_date: date|null  # YYYY-MM-DD for readability

# Health monitoring
health_status: string      # healthy | degraded | unreachable | dormant
last_health_check: datetime|null

# Context
recent_topics: list        # Last 3-5 active topics
data_policy:
  sensitivity: string      # low | medium | high | private
  rules: list              # What can/can't be shared here
  enforced_by: string      # Hook module name

# People
key_contacts: list         # Who's active in this conversation

# State
open_questions: list       # Unanswered questions
pending_items: list        # Action items tied to this conversation
```

## Naming Convention

Files are named: `{platform}-{identifier}.yaml`

Examples:
- `slack-all-misfits.yaml`
- `teams-coconut-private.yaml`
- `email-dole-case-tm03941209.yaml`
- `trello-todo-list.yaml`
- `github-openclaw-dm.yaml`

## Health Monitoring

A lightweight cron script (`scripts/channel-health/check.py`) runs every 30 minutes:

1. Groups channels by platform (one API call per platform, not per channel)
2. Checks reachability (can we read from this source?)
3. Checks activity (is `last_human_message` abnormally old for this channel's pattern?)
4. Writes results to `channels/health.json`
5. Main session reads `health.json` on heartbeat — only alerts on state changes

Health states:
- **healthy** — reachable, activity within expected window
- **degraded** — reachable but errors or unusual latency
- **unreachable** — API calls failing
- **dormant** — reachable but no activity for >7 days (not necessarily a problem)

## Adding a New Comm Source

1. Create a YAML file following the schema above
2. Add platform-specific health check in `scripts/channel-health/check.py`
3. The system auto-discovers new files in `channels/` — no config changes needed

## Hook Enforcement

The `channel-state-validator` hook module (planned) will:
- Validate new YAML files against this schema on write
- Reject files missing required fields
- Warn on sensitivity: high channels without data_policy rules
