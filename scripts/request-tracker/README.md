# Cross-Channel Request/Response Tracker

Tracks where requests originate and ensures responses are delivered back to the right channel.

## Problem

When a request comes in on one channel (e.g., Teams) but Coconut is also talking on another (e.g., Slack), the response often gets delivered only to the active channel, not back to where the request originated.

## How It Works

1. **Record**: When a request arrives, log its source channel + topic
2. **Match**: Before composing a response, check if it fulfills a tracked request
3. **Deliver**: Send response to the originating channel + mark as delivered
4. **Cleanup**: Auto-expire old entries after 72h

## CLI Usage

```bash
# Record a request from Teams
python3 request-tracker.py record --channel teams --chat-id "19:abc...123" --sender "Joel" --topic "research Tailscale ACLs"

# Find where a topic was requested
python3 request-tracker.py match --topic "Tailscale ACL research results"

# Mark delivered
python3 request-tracker.py deliver --request-id abc123def456

# Show pending requests
python3 request-tracker.py pending

# Stats
python3 request-tracker.py status

# Cleanup old entries
python3 request-tracker.py cleanup --hours 48
```

## Integration Points

- **Heartbeat cron**: Run `pending` during heartbeat to surface undelivered responses
- **Outbound message hook**: Check `match` before sending, route to origin channel
- **Inbound message handler**: Run `record` when processing new requests

## State

Persisted to `state/request-tracker.json`. Auto-prunes delivered entries after 7 days.

## Channels

| Channel | Key |
|---------|-----|
| Slack | `slack` |
| Teams | `teams` |
| Trello | `trello` |
| GitHub | `github` |
| Email | `email` |
| Cron/System | `cron` |
