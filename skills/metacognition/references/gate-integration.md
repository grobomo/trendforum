# Gate Integration — openclaw-gates

How to add metacognition enforcement to the openclaw-gates Plugin SDK plugin.

## Conflict Resolution Gate

A `before_tool_call` hook in openclaw-gates that:

1. Detects when the agent is about to write a spec or build artifact
2. Checks if any active lessons conflict with the action
3. Blocks if no CR document exists for the identified conflict

### Config Section

Add to openclaw-gates plugin config:

```json
{
  "conflictResolution": {
    "enabled": true,
    "mode": "log",
    "crDirectory": "memory/conflict-resolutions",
    "lessonsDirectory": "memory/lessons"
  }
}
```

### Modes

| Mode | Behavior |
|---|---|
| `log` | Detect conflicts, log to audit, don't block |
| `enforce` | Detect conflicts, block until CR document exists |

### Rollout

1. Start with `mode: "log"` — observe what it catches
2. Review audit logs for false positives
3. Switch to `mode: "enforce"` once validated

## Why Plugin SDK (not Managed Hooks)

Per lesson 002: managed hooks (`~/.openclaw/hooks/`) cannot block tool calls.
Only Plugin SDK hooks via `api.on("before_tool_call", ...)` can block.
Enforcement MUST use openclaw-gates (Plugin SDK), not managed hooks.
