---
name: heartbeat-enforce
description: "Enforces HEARTBEAT.md instructions on heartbeat polls — ensures the agent reads and follows the heartbeat checklist"
metadata:
  { "openclaw": { "emoji": "💓", "events": ["message:received"] } }
---

# Heartbeat Enforce

Intercepts incoming heartbeat messages and injects enforcement reminders to ensure the agent follows HEARTBEAT.md instructions strictly.

When a heartbeat poll arrives, this hook appends a reminder to the message that the agent MUST:
1. Read HEARTBEAT.md
2. Execute every task listed (not skip them)
3. Only reply HEARTBEAT_OK if HEARTBEAT.md is empty or has no actionable tasks
