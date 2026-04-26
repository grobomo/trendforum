# Metacognition Migration Analysis
Generated: 2026-04-26 01:03 CDT

## Executive Summary

- *8* existing cron jobs found
- *1* are metacognition-related (migration candidates)
- *7* are non-metacognition (will NOT be touched)
- *5* new modular modules ready
- *0* blockers
- *0* warnings

## ✅ No Blockers — Ready to Migrate

## Migration Candidates (will be replaced)

| Cron Name | Schedule | Model | Status | Errors |
|---|---|---|---|---|
| self-audit | every 60m | trendmicro-aiendpoint/claude-4 | ok | 0 |

## Non-Migration Crons (will NOT be touched)

- **schedule-briefing** — ok
- **session-health** — ok
- **claude-tab-monitor** — ok
- **slack-missed-detector** — ok
- **trello-work** — error
- **Memory Dreaming Promotion** — ok
- **daily-squad-scheduler** — unknown

## Old Metacognition Files (will be archived)

- `/home/ubu/openclaw-dm/scripts/metacognition/self-audit.py` — exists (11811 bytes, modified 2026-04-25)
- `/home/ubu/.openclaw/workspace/scripts/metacognition/analyze_sessions.py` — exists (9031 bytes, modified 2026-04-25)
- `/home/ubu/.openclaw/workspace/scripts/metacognition-check.md` — exists (4079 bytes, modified 2026-04-23)
- `/home/ubu/.openclaw/workspace/scripts/metacognition-rules.md` — exists (2273 bytes, modified 2026-04-22)
- `/home/ubu/.openclaw/workspace/scripts/metacognition-big-review.md` — exists (3586 bytes, modified 2026-04-21)

## New Modular System

- **conflict-resolution** — `/home/ubu/.openclaw/workspace/skills/metacognition/scripts/modules/conflict-resolution.py` (5719 bytes)
- **decision-check** — `/home/ubu/.openclaw/workspace/skills/metacognition/scripts/modules/decision-check.py` (2290 bytes)
- **lesson-review** — `/home/ubu/.openclaw/workspace/skills/metacognition/scripts/modules/lesson-review.py` (3930 bytes)
- **pattern-detector** — `/home/ubu/.openclaw/workspace/skills/metacognition/scripts/modules/pattern-detector.py` (5087 bytes)
- **session-analyzer** — `/home/ubu/.openclaw/workspace/skills/metacognition/scripts/modules/session-analyzer.py` (5576 bytes)

## Dry Run Results

### Quick Tier (dry run)
```
🧠 Metacognition quick tier — 2026-04-26 01:03
   Modules: session-analyzer, decision-check
  [DRY RUN] session-analyzer — ✅
  [DRY RUN] decision-check — ✅
```

### Deep Tier (dry run)
```
🧠 Metacognition deep tier — 2026-04-26 01:03
   Modules: conflict-resolution, lesson-review, pattern-detector
  [DRY RUN] conflict-resolution — ✅
  [DRY RUN] lesson-review — ✅
  [DRY RUN] pattern-detector — ✅
```

## Live Test Results (demonstration)

### Quick Tier (live)
```
🧠 Metacognition quick tier — 2026-04-26 01:03
   Modules: session-analyzer, decision-check

--- session-analyzer ---
✅ Sessions: 210 | Compactions: 11 | Top tools: exec=2433, read=387, message=320, process=303, mcp-manager__mcpm=189
  Result: ✅ ok

--- decision-check ---
ℹ️  0 active, 0 blocked decisions
  Result: ✅ ok

--- Summary ---
  ✅ session-analyzer
  ✅ decision-check
```

### Deep Tier (live)
```
🧠 Metacognition deep tier — 2026-04-26 01:03
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

### Step 1: Backup (automatic)
- Date-stamped copies of all affected files → `.archive/metacog-migration-YYYYMMDD-HHMMSS/`
- Cron job configs exported to JSON backup

### Step 2: Replace cron jobs
- Disable old `self-audit` cron
- Create new `metacog-quick` cron (every 15m, Haiku, runs metacog-runner.py --tier quick)
- Create new `metacog-deep` cron (every 1h, Sonnet, runs metacog-runner.py --tier deep)

### Step 3: Archive old files
- Move old metacog scripts to `.archive/` (never delete)

### Step 4: Verify
- Run both tiers and confirm output matches expectations
- Compare with last known-good output from old system
- Monitor for 24h via audit logs

### Rollback Plan
- Restore cron jobs from JSON backup
- Restore files from `.archive/` backup
- All backups are date-stamped and never overwritten
