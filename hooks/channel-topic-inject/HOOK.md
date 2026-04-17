---
name: channel-topic-inject
description: "Injects channel topic/purpose context into inbound messages so the agent stays on-topic"
metadata:
  { "openclaw": { "emoji": "📋", "events": ["message:received"] } }
---

# Channel Topic Inject

Injects a system-level reminder about the current Slack channel's topic/purpose when a message arrives. This helps the agent stay on-topic without explicit enforcement.

Channels:
- `#all-misfits` (C0ATFDQRGRL) — Customer/business chat
- `#coco-chat` (C0ATJE19YRY) — Coconut processes & infrastructure
- `#social` (C0ATB4AS9PD) — Casual/social
