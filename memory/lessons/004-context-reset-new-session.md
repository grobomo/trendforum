# Lesson: How to Launch Claude Code Sessions via context-reset/new_session.py

## Observation
2026-04-24: When asked to launch Claude Code for the openclaw-dm project, I bypassed new_session.py and launched with `claude --permission-mode bypassPermissions --print` directly. Joel pointed out that new_session.py handles everything — permissions, state handoff, stop hooks — and I should not add any flags.

## The System (context-reset project)

**Location:** `/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/context-reset/`
**Repo:** grobomo/context-reset (public)

### Two scripts, two purposes:
1. **`new_session.py`** — Opens a NEW Claude Code session in any project. **Never** closes the calling tab. Used for cross-project work or fresh sessions.
2. **`context_reset.py`** — Same-project reset. **Always** closes the calling tab. Used when context window fills up.

### How it works:
1. Reads last 500 JSONL transcript lines (efficient reverse-read)
2. Parses into readable conversation text → writes `SESSION_STATE.md` (~8K tokens)
3. Opens new Windows Terminal tab with `claude '<prompt>'` — NO extra flags needed
4. Waits for new Claude process (process count check)
5. Verifies new session is working (transcript file activity)
6. Kills old tab (or preserves with `--no-close`)

### Key: No permission flags needed
The script calls `ensure_workspace_trusted()` which writes trust state directly to `~/.claude.json` (`projects[path].hasTrustDialogAccepted = true`). The new session launches as plain `claude '<prompt>'` and trusts the workspace automatically.

**DO NOT add `--dangerously-skip-permissions`, `--permission-mode bypassPermissions`, or `--print` flags.** These change Claude Code's behavior in ways the stop-hook system doesn't expect.

### How to call it from OpenClaw (Coconut):
```bash
python3 /mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/context-reset/new_session.py \
  --project-dir /path/to/project \
  --prompt "Your task prompt here" \
  --no-close
```

Use `--no-close` when launching from Coconut (we don't have a tab to close).

### Stop Hook: auto-continue.js
When Claude Code tries to stop, the stop hook (`~/.claude/hooks/run-modules/Stop/auto-continue.js`) fires and:
1. Checks for preserved-tab idle flag (if set, allows stop)
2. Otherwise, returns `{decision: "block", reason: <stop-message.txt>}`

**stop-message.txt** tells Claude to:
1. Check TODO.md — if tasks remain, do the next one
2. Scan JSONL logs for incomplete work
3. TEST what was built
4. Organize/optimize
5. Zoom out — why does this exist, how to share it
6. **OPENCLAW CHECKIN** — report status via `openclaw-checkin.py`
7. If context is long → save state to TODO.md, run context_reset.py
8. For cross-project work → run new_session.py

### OpenClaw Checkin (claude-checkin.py)
**Location:** `/mnt/c/Users/joelg/.claude/scripts/openclaw-checkin.py`

Claude Code calls this to report status back to OpenClaw/Coconut:
```bash
wsl -e bash -c 'python3 /mnt/c/Users/joelg/.claude/scripts/openclaw-checkin.py \
  --status done --task TXXX --detail "brief summary" \
  --project PROJECT_NAME --fire-and-forget'
```

Statuses: `done | blocked | progress | tests | error`
`--fire-and-forget` is non-blocking (5s timeout). Posts to OpenClaw's chat API at localhost:18789.

## My Mistakes
1. Didn't research the context-reset project before launching
2. Added `--permission-mode bypassPermissions --print` flags — bypassing the entire stop-hook/auto-continue system
3. Using `--print` mode means Claude runs one-shot and exits — it won't loop through TODO.md tasks via the stop hook
4. The right approach: plain `new_session.py --project-dir <dir> --prompt <task>` — the system handles everything

## Source
- Project: grobomo/context-reset
- Stop hook: `~/.claude/hooks/run-modules/Stop/auto-continue.js`
- Stop message: `~/.claude/hooks/run-modules/Stop/stop-message.txt`
- Checkin script: `~/.claude/scripts/openclaw-checkin.py`
- Conversation with: Joel, 2026-04-24

## Retrieval Triggers
- Launching Claude Code
- context-reset, new_session.py
- "spawn Claude Code session"
- coding-agent delegation
- Claude Code permissions, flags
- openclaw-checkin, claude-checkin
- stop hooks, auto-continue
