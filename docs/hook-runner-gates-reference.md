# Hook-Runner Gates System — Reference & Design Doc

## What I Learned (2026-04-25)

### Architecture

The hook-runner-gates plugin is a **modular, file-based gate system**. Each gate is a single `.js` file (CommonJS) that receives tool call context and returns `null` (allow) or `{ decision: "block", reason: "..." }`.

```
~/.openclaw/extensions/hook-runner-gates/
├── index.ts              ← Plugin entry, loads modules dynamically
├── modules.yaml          ← Enable/disable toggles per module
├── modules/
│   ├── before_tool_call/ ← 19 gate modules (fire before every tool call)
│   ├── after_tool_call/  ← 8 modules (fire after, for logging/review)
│   ├── before_agent_reply/ ← 1 module (pre-reply checks)
│   └── session_start/    ← 1 module (session init reminders)
└── openclaw.plugin.json  ← Plugin manifest + schema
```

### Module Contract

```javascript
// TOOLS: exec, write, edit        ← which tools trigger this module
// WHY: <reason this gate exists>  ← human context for future review

module.exports = function(input) {
  // input.tool_name = "exec" | "write" | "edit" | "message" | etc.
  // input.tool_input = { command: "...", path: "...", ... }
  
  // Return null → allow the tool call
  // Return { decision: "block", reason: "..." } → block with explanation
  return null;
};
```

**Important:** The `// TOOLS:` header is parsed by the loader. OpenClaw uses `exec` (not `Bash`). If you write `// TOOLS: Bash`, the module silently never fires. This was a bug that went unnoticed for hours.

### Project Scoping

Modules can be scoped to specific projects via subdirectories:

```
modules/before_tool_call/<projectname>/*.js
```

Only loaded when `basename(CLAUDE_PROJECT_DIR || cwd) === <projectname>`. This means Claude Code sessions working on project `openclaw` will load gates from `modules/before_tool_call/openclaw/` in addition to global gates.

### Key Differences: hook-runner-gates vs coconut-guardrails

The split is about *who is being governed*, not gate complexity:

| Aspect | hook-runner-gates | coconut-guardrails |
|--------|------------------|-------------------|
| **Governs** | Claude Code sessions (Windows terminal tabs) | OpenClaw/Coconut (agent sessions) |
| **Purpose** | Behavioral enforcement for Claude Code | Behavioral enforcement for Coconut |
| Format | .js gate modules | TypeScript plugin code |
| Config | modules.yaml | openclaw.json plugin config |
| Scope | Project-scoped possible | Global |
| Adding gates | Drop a .js file | Edit index.ts + restart |

Both use the same hook-runner module system and the same contract (return `null` to allow, `{ decision: "block", reason }` to block). The difference is the target agent.

### When to Add a Gate (Self-Reference)

Add to **hook-runner-gates** when:
1. Claude Code needs a behavioral constraint ("never do X in this project")
2. A pattern repeats across Claude Code sessions
3. Project-scoped rules needed (scope to project subdirectory)

Add to **coconut-guardrails** when:
1. Coconut (OpenClaw agent) needs a behavioral constraint
2. Inner voice, config-safety, todo enforcement, or other self-governance
3. State, file I/O, or LLM review needed for the check

## Plugin Directory Structure (IMPORTANT)

### Current Problem
- Source code lives in `~/.openclaw/plugins/coconut-guardrails/` (git repo)
- Gateway loads from `~/.openclaw/extensions/coconut-guardrails/` (runtime copy)
- Manual sync required → easy to forget → schema mismatches break gateway

### Correct Architecture (TODO)
- `~/.openclaw/extensions/` = where OpenClaw expects all plugin files (runtime)
- `~/.openclaw/plugins/` = should NOT be used for runtime loading
- Source repos should be independent git repos (e.g., `tmemu/coconut-guardrails`)
- Deploy = build/copy from repo → extensions dir + gateway restart

### Migration Plan
1. Create `joel-ginsberg_tmemu/coconut-guardrails` GitHub repo
2. Push current source from `~/.openclaw/plugins/coconut-guardrails/`
3. Make `~/.openclaw/extensions/coconut-guardrails/` the deploy target
4. Build deploy script: `git pull` from repo → copy to extensions → backup → restart
5. Remove or archive `~/.openclaw/plugins/coconut-guardrails/`

## Existing Gate Modules (Inventory)

### before_tool_call (19 modules)
| Module | Purpose |
|--------|---------|
| archive-not-delete | Block rm/unlink — archive instead |
| claude-p-pattern | Block Claude --print patterns |
| commit-quality-gate | Enforce commit message quality |
| crlf-ssh-key-check | Detect CRLF in SSH keys |
| disk-space-guard | Block writes when disk is low |
| force-push-gate | Block git force-push |
| git-destructive-guard | Block destructive git ops |
| git-rebase-safety | Block unsafe rebases |
| no-focus-steal | Prevent context switching |
| no-fragile-heuristics | Block brittle pattern matching |
| no-hardcoded-paths | Detect hardcoded absolute paths |
| no-nested-claude | Block spawning Claude inside Claude |
| no-unnecessary-sleep | Block long sleep commands |
| root-cause-gate | Force root cause analysis |
| secret-scan-gate | Detect secrets in commands |
| task-tracking-gate | Enforce task tracking |
| todo-enforcement | Block work without reading todo.md |
| unresolved-issues-gate | Block deployment with open issues |
| victory-declaration-gate | Block premature "done" claims |

### after_tool_call (8 modules)
commit-msg-check, crlf-detector, test-coverage-check, result-review-gate, rule-hygiene, empty-output-detector, disk-space-detect, troubleshoot-detector

### before_agent_reply (1 module)
auto-continue

### session_start (1 module)
session-start-reminder

---
_Written: 2026-04-25 by Coconut. Update when gates are added/modified._
