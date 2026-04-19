# OpenClaw SDK Hooks — Reference & Our Setup

*Documented 2026-04-19*

## Our Active Plugins

### hook-runner-gates (v0.4.0)
- Location: `~/.openclaw/extensions/hook-runner-gates/`
- Source: `/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/hook-runner/openclaw-plugin/`
- 27 modules ported from Claude Code hook-runner to OpenClaw Plugin SDK
  - 17 `before_tool_call` gates (force-push, secret-scan, git-destructive, etc.)
  - 8 `after_tool_call` gates (commit-msg-check, crlf-detector, etc.)
  - 1 `before_agent_reply` (auto-continue)
  - 1 `session_start` (session-start-reminder)
- Uses `definePluginEntry` + `api.on("before_tool_call")` pattern
- Full mapping: `hook-runner/docs/T472-openclaw-mapping.md` (94 modules, 70% portable)

### coconut-guardrails (v0.1.0)
- Location: `~/.openclaw/extensions/coconut-guardrails/`
- Two enforcement layers:
  1. Static rules — regex/pattern-based, fast, deterministic
  2. Haiku inner voice — LLM-based content review before outbound messages
- Hooks: `before_tool_call` + `message_sending`
- Has emergency shutoff, per-channel rules, audit logging
- **This is where new Coconut-specific gates go** (e.g., duplicate message detection)

## Key Plugin SDK Hooks for Blocking

### `before_tool_call`
- Fires before any tool call (including `message(action=send)`)
- Return `{ block: true, blockReason: "..." }` to prevent the call
- Return `{ requireApproval: true }` to pause and ask user
- Can modify params: `{ params: { ...modified } }`
- **Fail-closed**: hook errors → tool call blocked
- Sequential; `block: true` is terminal

### `message_sending`
- Fires before outbound message delivery to channel
- Return `{ cancel: true }` to suppress the send
- Can modify content: `{ content: "modified text" }`
- Sequential; `cancel: true` is terminal

### `after_tool_call` / `message_sent`
- Fire-and-forget (parallel), cannot block
- Good for logging/auditing

## Conversion Pattern (hook-runner → OpenClaw)

| Hook-Runner | OpenClaw Plugin SDK |
|---|---|
| `module.exports = function(input)` | `api.on("before_tool_call", (input) => ...)` |
| `input.tool_name` | `input.tool` |
| `input.tool_input.command` | `input.args.command` |
| `return null` (pass) | `return { action: "allow" }` |
| `return { decision: "block", reason }` | `return { action: "deny", reason }` |

## TODO

- [ ] Add duplicate-message detection gate to coconut-guardrails
  - Track recent sent messages per channel (content hash + timestamp)
  - Block/cancel when substantially similar content sent within N minutes
  - This prevents the triple-send problem Joel identified (2026-04-19)
