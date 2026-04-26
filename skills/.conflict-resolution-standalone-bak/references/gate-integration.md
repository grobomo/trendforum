# Gate Integration — openclaw-gates

How to add conflict-resolution enforcement to the openclaw-gates Plugin SDK plugin.

## Architecture

The conflict-resolution gate is a `before_tool_call` hook in openclaw-gates that:

1. Detects when the agent is about to write a spec or build artifact
2. Checks if any active lessons conflict with the action
3. Blocks if no CR document exists for the identified conflict

## Config Section

Add to `openclaw.plugin.json` config or the plugin's runtime config:

```json
{
  "conflictResolution": {
    "enabled": true,
    "mode": "log",
    "crDirectory": "memory/conflict-resolutions",
    "specPatterns": [
      "specs/.*\\.md$",
      "SPEC\\.md$",
      ".*-spec\\.md$"
    ],
    "lessonsDirectory": "memory/lessons"
  }
}
```

### Config fields

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | boolean | false | Enable/disable the gate |
| `mode` | `"enforce"` or `"log"` | `"log"` | Log-only or hard-block |
| `crDirectory` | string | `"memory/conflict-resolutions"` | Where CR docs live |
| `specPatterns` | string[] | see above | Regex patterns for spec files |
| `lessonsDirectory` | string | `"memory/lessons"` | Where lesson files live |

## Implementation Pattern

Add to `openclaw-gates/index.ts` in the `before_tool_call` handler:

```typescript
// ── Conflict Resolution Gate ──────────────────────────────────────
if (config.conflictResolution?.enabled) {
  const crConfig = config.conflictResolution;
  const filePath = typeof event.params.path === "string" ? event.params.path : "";
  
  // Only check on write/edit to spec files
  if (["write", "edit"].includes(event.toolName)) {
    const isSpecFile = (crConfig.specPatterns || []).some(p => 
      new RegExp(p, "i").test(filePath)
    );
    
    if (isSpecFile) {
      // Check for unresolved conflicts
      // (Implementation: scan lessons dir, check for conflicts with spec content,
      //  verify CR doc exists if conflict detected)
      const isLogOnly = crConfig.mode === "log";
      // ... gate logic
    }
  }
}
```

## Rollout Plan

1. Start with `mode: "log"` — observe what it would catch
2. Review audit logs for false positives
3. Switch to `mode: "enforce"` once validated
4. Add to #coco-metacognition reports

## Why Plugin SDK (not Managed Hooks)

This gate needs `before_tool_call` to block spec writes that have unresolved conflicts.
Managed hooks (`~/.openclaw/hooks/`) only support event-level lifecycle hooks
(`message:sent`, `command:new`, etc.) — they cannot intercept or block tool calls.

Only Plugin SDK hooks via `api.on("before_tool_call", ...)` can block.
This is documented in lesson 002 (`memory/lessons/002-managed-vs-plugin-hooks.md`).
