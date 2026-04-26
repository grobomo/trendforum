# CR-001: Hook-Runner Module vs Plugin SDK for Blocking Gates

## Status
`pending-review`

## Date
2026-04-25

## Conflict Summary
Trello card spec says to build `pm-mode-gate` as a hook-runner module (.js), but lesson 002 documents that hook-runner modules cannot perform `before_tool_call` blocking — only Plugin SDK hooks can.

## Side A
- **Source:** Trello card — pm-mode-gate task
- **Says:** "Must be a hook-runner module (.js), not a guardrails plugin rule."
- **Date written:** 2026-04-25 (card creation)

## Side B
- **Source:** Lesson 002 — `memory/lessons/002-managed-vs-plugin-hooks.md`
- **Says:** "For behavioral blocking (stopping an action before it happens), you MUST use Plugin SDK hooks. Managed hooks can only audit after the fact." Two hook systems exist: (1) Managed hooks — event-level only, (2) Plugin SDK hooks — full 28-hook set including before_tool_call.
- **Date written:** 2026-04-19

## Research

### What the docs say
OpenClaw docs confirm two separate hook systems:
- Managed hooks (`~/.openclaw/hooks/`) — lifecycle events only
- Plugin SDK (`api.registerHook()` in plugins) — full tool-level interception

The hook-runner module system (claude-code-gates) IS a Plugin SDK plugin, but it targets Claude Code agents specifically. The openclaw-gates plugin targets the main OpenClaw session.

### What the code says
- `claude-code-gates/index.ts` — registers `before_tool_call` via Plugin SDK. Loads modules from `modules/before_tool_call/*.js`. These modules CAN block.
- `openclaw-gates/index.ts` — separate Plugin SDK plugin for main session. Also uses `before_tool_call`.
- Both are Plugin SDK plugins, NOT managed hooks.

### Historical context
- Lesson 002 was written 2026-04-19 when the distinction was first discovered
- The card spec may have been written without accounting for lesson 002
- The confusion: "hook-runner module" (claude-code-gates) vs "managed hooks" (~/.openclaw/hooks/) — they're actually DIFFERENT things

### Key insight
The card says "hook-runner module (.js)" which actually means a claude-code-gates module — and those CAN do before_tool_call! The conflict may be a misreading: lesson 002 says MANAGED hooks can't block, but hook-runner modules are Plugin SDK modules that CAN block.

However, pm-mode-gate needs to run in the MAIN session (OpenClaw), not in Claude Code. Claude-code-gates targets Claude Code agents. So the gate needs to be in openclaw-gates, not claude-code-gates.

### Related lessons
- 003: Instructions alone don't prevent bad behavior — need deterministic hooks
- 006: Automate everything — don't rely on self to enforce rules

## Options

### Option 1: Build as claude-code-gates hook-runner module
- **Approach:** Add pm-mode-gate.js to claude-code-gates/modules/before_tool_call/
- **Pros:** Follows the card spec literally; hook-runner modules CAN block (they're Plugin SDK)
- **Cons:** Wrong scope — claude-code-gates targets Claude Code agents, not the main session
- **Impact:** Gate would only fire in Claude Code, not in Coconut's main session

### Option 2: Build as openclaw-gates module
- **Approach:** Add pm-mode-gate logic to openclaw-gates/index.ts
- **Pros:** Correct scope (main session); Plugin SDK so it CAN block; consistent with existing gates
- **Cons:** Doesn't match card spec wording ("hook-runner module")
- **Impact:** Gate fires in the right context; card spec needs updating

### Option 3: Build in both
- **Approach:** Hook-runner module for Claude Code + openclaw-gates for main session
- **Pros:** Full coverage
- **Cons:** Duplicated logic; overkill for current needs
- **Impact:** Maintenance burden

## Decision
*Pending Joel's review.* Recommended: Option 2 (openclaw-gates). The card spec wording was likely imprecise — the intent is "blocking gate" which requires Plugin SDK, and the main session is the right scope.

## Resolution Actions
- [ ] Get Joel's decision on approach
- [ ] Update lesson 002 to clarify the distinction between hook-runner modules (Plugin SDK) and managed hooks more explicitly
- [ ] Update the Trello card spec with the correct architecture
- [ ] Build the gate in the chosen location
- [ ] Post to #coco-metacognition

## Resolved By
Pending — escalated to Joel — 2026-04-25
