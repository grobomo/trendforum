# Metacognition Migration Analysis
Generated: 2026-04-26 01:21 CDT

## Executive Summary

- **0** existing cron jobs analyzed
- **0** classified as `replace` (new modules cover them)
- **0** classified as `coexist` (will NOT be touched)
- **0** classified as `review` (human decision needed)
- **6** new modular modules ready
- **0** blockers
- **0** warnings

## ✅ No Blockers — Ready to Migrate

## Cron Classification (dynamically determined)

| Cron Name | Classification | Reason | Matching Modules |
|---|---|---|---|

## Old Metacognition Files (will be archived, never deleted)

- `/home/ubu/.openclaw/workspace/scripts/metacognition/analyze_sessions.py` — 9031 bytes, modified 2026-04-25
- `/home/ubu/.openclaw/workspace/scripts/metacognition-big-review.md` — 3586 bytes, modified 2026-04-21
- `/home/ubu/.openclaw/workspace/scripts/metacognition-check.md` — 4079 bytes, modified 2026-04-23
- `/home/ubu/.openclaw/workspace/scripts/metacognition-rules.md` — 2273 bytes, modified 2026-04-22
- `/home/ubu/openclaw-dm/scripts/metacognition/self-audit.py` — 11811 bytes, modified 2026-04-25

## New Modular System

- **change-control** (quick) — Gate deployment change control — ensures log-before-enforce,
- **conflict-resolution** (deep) — Detect and resolve conflicts between lessons, specs, and hoo
- **decision-check** (quick) — Check DECISIONS.md for contradictions or stale decisions
- **lesson-review** (deep) — Review lessons board, check for new lessons, apply resolved 
- **pattern-detector** (deep) — Detect circular rebuilds, repeated failures, token hemorrhag
- **session-analyzer** (quick) — Quantitative session analysis — tool counts, command frequen

## Live Demo Results

### Quick Tier
```
🧠 Metacognition quick tier — 2026-04-26 01:21
   Modules: session-analyzer, decision-check, change-control

--- session-analyzer ---
✅ Sessions: 216 | Compactions: 12 | Top tools: exec=2563, read=397, message=324, process=304, mcp-manager__mcpm=205
  Result: ✅ ok

--- decision-check ---
ℹ️  0 active, 0 blocked decisions
  Result: ✅ ok

--- change-control ---
=== Change Control Assessment (2026-04-26 06:21 UTC) ===
Gates assessed: 4

✅ research-gate [log] — 0 audit events

✅ todo-gate [log] — 0 audit events

🚨 rule:bias-to-action [enforce] — 0 audit events
   → Gate is in ENFORCE mode but only has 0 audit events (minimum: 20). Was log-mode monitoring sufficient?
   → Gate is in ENFORCE mode with ZERO audit evidence. This gate was likely deployed directly to enforce without any log-mode monitoring.

🚨 rule:archive-before-delete [enforce] — 0 audit events
   → Gate is in ENFORCE mode but only has 0 audit events (minimum: 20). Was log-mode monitoring sufficient?
   → Gate is in ENFORCE mode with ZERO audit evidence. This gate was likely deployed directly to enforce without any log-mode monitoring.

📋 Recent gate-related config changes:
   de2e4a1 rename: hook-log.jsonl → audit-logger.jsonl
   4d7d27c fix: use existing hook-log.jsonl, archive redundant audit-logger
   5c28902 feat: research-gate + autonomous work loop spec
   f87df82 feat: add audit-logger module to claude-code-gates
   8ddc73c feat: add task-tracking-gate hook (P0) — blocks work without registered task

🚨 2 CRITICAL: Gates deployed to enforce without monitoring!
  Result: ✅ ok

--- Summary ---
  ✅ session-analyzer
  ✅ decision-check
  ✅ change-control
```

### Deep Tier
```
🧠 Metacognition deep tier — 2026-04-26 01:21
   Modules: conflict-resolution, lesson-review, pattern-detector

--- conflict-resolution ---
Scanned 7 lessons, 1 CR docs
📋 1 finding(s):
  - Unresolved CR: CR-001: Hook-Runner Module vs Plugin SDK for Blocking Gates (CR-001-hook-architecture-blocking.md)
  Result: 📋 findings

--- lesson-review ---
ℹ️  Scanned 7 lesson files
📋 9 finding(s):
  📋 001-verify-before-claiming.md: hook status is 'new' — verify if implemented
  ℹ️ 001-verify-before-claiming.md: 3 unverified item(s)
  📋 003-customer-data-in-slack.md: hook status is 'new' — verify if implemented
  ℹ️ 003-customer-data-in-slack.md: 6 unverified item(s)
  🟡 004-context-reset-new-session.md: missing sections: Lesson/Principle
  📋 004-poll-all-permanently-dead.md: hook status is 'new' — verify if implemented
  ℹ️ 004-poll-all-permanently-dead.md: 3 unverified item(s)
  🟡 005-gh-auto-account-switching.md: missing sections: Lesson/Principle
  🔴 Duplicate lesson number 004: 004-context-reset-new-session.md and 004-poll-all-permanently-dead.md
  Result: 📋 findings

--- pattern-detector ---
📋 5 pattern(s) detected:
  🟡 Repeated error (239x): {
  "status": "error",
  "tool": "exec",
  "error": "exec pr...
  🟡 Repeated error (26x): usage: check_gaps.py [-h] [--minutes MINUTES] [--enriched]
c...
  🟡 Repeated error (22x): usage: tracker.py [-h]
                  {record,respond,pen...
  🟡 Repeated error (22x): error: too many arguments for 'message'. Expected 0 argument...
  🟡 Repeated error (12x): {
  "status": "error",
  "tool": "edit",
  "error": "TODO EN...
  Result: 📋 findings

--- Summary ---
  📋 conflict-resolution
  📋 lesson-review
  📋 pattern-detector
```

## Benefits of Migration

- Modular enable/disable per metacognition task (no monolithic cron prompts)
- Two-tier model: quick (15m) for cheap checks, deep (1h) for expensive analysis
- Independent module testing via --module flag
- Structured output to daily logs instead of ad-hoc appending
- Conflict resolution: automated detection of lesson/spec contradictions
- Pattern detection: catches circular rebuilds and token waste automatically
- Lesson review: structural integrity checks on lesson files
- Dry-run mode for previewing what each cycle would do
- Shareable as an OpenClaw skill (.skill package)

## Migration Plan

### Step 1: Backup
- Export full cron table to JSON in `.archive/`
- Date-stamped copy of all old metacog scripts
- Copy existing metacognition output
- MANIFEST.md with restore instructions

### Step 2: Execute
- Reads migration plan JSON from analysis step (single source of truth)
- Only disables crons classified as `replace`
- Skips crons classified as `review` unless human confirmed
- Creates `metacog-quick` (15m, Haiku) and `metacog-deep` (1h, Sonnet)
- Archives old scripts to `.archive/` (move, never delete)

### Step 3: Verify
- Confirms new crons exist and enabled
- Confirms replaced crons disabled (not deleted)
- Runs both tiers live
- Confirms coexist crons untouched

### Rollback
- Re-enables replaced crons from backup
- Removes new metacog crons
- Restores archived scripts
