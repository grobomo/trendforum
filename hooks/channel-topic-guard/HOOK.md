---
name: channel-topic-guard
description: "LLM-powered inner voice that reviews outbound messages against channel rules before delivery"
metadata:
  { "openclaw": { "emoji": "🧠", "events": ["message:sent"] } }
---

# Channel Topic Guard — Inner Voice

Uses a lightweight Haiku LLM call to review every outbound message against static channel rules
defined in `~/.openclaw/channel-rules.json`. Acts as a "little voice in your head" that catches
misrouted or off-topic content before it reaches the channel.

Covers all comm methods: Slack channels, Teams chats, GitHub, and email.

On BLOCK, logs a warning with the reason and suggested redirect channel.
