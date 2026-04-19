# Hook-Runner Study — Lessons from Claude Code's System

*Studied 2026-04-19 from ~/.claude/hooks/hook-log.jsonl + .jsonl.1*

## System Architecture

- Central log: `~/.claude/hooks/hook-log.jsonl` (JSONL, 10MB rotation)
- Health log: `~/.claude/hooks/hook-health.jsonl` (runner-level timing)
- 66 unique modules across 4 event types
- Every module logs every invocation — pass AND block — with timing (ms)

## Scale

- 44,041 entries in rotated log + 2,253 in current = ~46K total
- 40,772 PreToolUse, 3,060 PostToolUse, 143 SessionStart, 43 Stop, 23 UserPromptSubmit
- 323 blocks out of 44,041 = 0.7% block rate (most pass quietly)
- 6ms average per module — fast enough to run 30+ modules per tool call without noticeable delay

## Block Reasons — The WHY Pattern

Every block reason has structure:
1. **GATE NAME** — what rule was violated
2. **What happened** — the specific action being blocked
3. **WHY** — the incident/lesson that created this rule
4. **REQUIRED** — what to do instead (actionable redirect)

Examples:
- `WORKTREE GATE: Edits blocked — you are in the main checkout.`
  `WHY: Multiple Claude tabs work on this project simultaneously.`
  `REQUIRED: Call scripts/make-worktree.sh <task> to create a worktree.`

- `REMOTE TRACKING GATE: Branch has no remote tracking.`
  `WHY: Untracked branches are invisible on GitHub Mobile.`

- `DESTRUCTIVE: git reset --hard destroys uncommitted changes.`
  `Alternatives: git stash — save changes for later`

## Top Blocking Modules (from history)

1. gsd-plan-gate (68) — blocks work without a plan/spec
2. git-destructive-guard (40) — blocks git reset --hard, checkout ., clean -f
3. auto-continue (30) — blocks lazy stops (listing options instead of doing work)
4. test-coverage-check (28) — blocks edits without running tests
5. spec-gate (28) — blocks edits on main without feature branch
6. branch-pr-gate (23) — blocks committing to wrong branch
7. archive-not-delete (21) — blocks rm -rf, requires archive instead
8. no-rules-gate (17) — blocks writing to ~/.claude/rules/
9. force-push-gate (17) — blocks force-push to main/master

## Log Entry Format

```json
{
  "ts": "2026-04-19T07:15:39.364Z",
  "event": "PreToolUse",
  "module": "enforcement-gate",
  "result": "block",        // "pass" | "block" | "text" | "integrity"
  "tool": "Edit",
  "file": "plugin.json",    // optional, basename only
  "cmd": "git checkout...", // optional, truncated to 120 chars
  "reason": "...",          // only on blocks, truncated to 200 chars
  "project": "claude-code-skills",
  "ms": 663
}
```

## What OpenClaw Needs (My System)

The equivalent for OpenClaw's before_tool_call hooks:

1. **Central log file**: `~/.openclaw/logs/hook-log.jsonl`
   - Log every hook invocation (pass + block) from both plugins
   - Same JSONL format: ts, event, module, result, tool, reason, ms
   - 10MB rotation

2. **WHY in every blockReason**: Every gate must explain the incident that created it
   - Not just "BLOCKED: duplicate message" but "WHY: On 2026-04-19, sent the same damage report 3 times with different formatting. Session compaction caused re-processing."

3. **Self-review during heartbeats**: Periodically read hook-log.jsonl, spot patterns, and improve gates

## Key Principle

The model never gets a vote. The Gateway enforces before execution.
Instruction files = general principles. Hook modules = specific behavioral rules.
Post-tool hooks = async audit only. Everything enforcement = before_tool_call.
