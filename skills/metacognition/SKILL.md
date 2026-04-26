---
name: metacognition
description: >-
  Modular metacognition system for AI self-reflection, pattern detection, and
  self-improvement. Runs as cron jobs at two tiers: lightweight (15m) for fast
  checks, and deep-think (1h) for analysis. Modules are independently
  enable/disable-able. Use when: (1) setting up metacognition cron jobs,
  (2) adding/editing/disabling metacognition modules, (3) running a
  metacognition cycle manually, (4) reviewing metacognition output,
  (5) resolving knowledge conflicts between lessons/specs/hooks.
  Triggers on: "metacognition", "self-reflection", "self-audit", "conflict
  resolution", "lesson conflict", "architecture conflict", "knowledge conflict",
  "thinking about thinking", "metacog module", "metacog cron".
  Required dependency: openclaw-gates (enforcement via Plugin SDK hooks).
---

# Metacognition

Modular self-reflection system. Each metacognition task is an independent module
with its own tier, config, and enable/disable toggle.

## Architecture

```
metacognition/
├── modules.yaml              # Module registry (enable/disable, tier, config)
├── modules/
│   ├── session-analyzer.py   # Quantitative session analysis
│   ├── conflict-resolution.py # Detect + resolve knowledge conflicts
│   ├── lesson-review.py      # Check lessons board, find new lessons
│   ├── decision-check.py     # Verify decisions aren't being contradicted
│   └── pattern-detector.py   # Detect anti-patterns (circular rebuilds, etc.)
└── output/
    └── YYYY-MM-DD.md         # Daily metacognition log
```

## Two-Tier Cron Model

| Tier | Interval | Model | Purpose |
|---|---|---|---|
| `quick` | 15 min | Haiku/Sonnet | Fast checks: session stats, stale state, simple flags |
| `deep` | 1 hour | Sonnet/Opus | Analysis: conflict resolution, lesson synthesis, pattern detection |

Modules declare their tier in `modules.yaml`. The cron runner loads only modules
matching the current tier.

## modules.yaml Format

```yaml
# Module registry — each module is independently toggleable
modules:
  session-analyzer:
    enabled: true
    tier: quick
    description: Quantitative session analysis (tool counts, anti-patterns)

  conflict-resolution:
    enabled: true
    tier: deep
    description: Detect and resolve conflicts between lessons, specs, and hooks
    config:
      cr_directory: memory/conflict-resolutions
      lessons_directory: memory/lessons
      auto_resolve_factual: true    # Auto-resolve factual errors
      escalate_architecture: true   # Escalate architecture decisions to human

  lesson-review:
    enabled: true
    tier: deep
    description: Review lessons board, check for new lessons, move Applied ones
    config:
      lessons_board_id: bZudEKUZ

  decision-check:
    enabled: true
    tier: quick
    description: Check DECISIONS.md for contradictions or stale decisions

  pattern-detector:
    enabled: true
    tier: deep
    description: Detect circular rebuilds, repeated failures, token waste
```

## Running Metacognition

### Via cron (automatic)

The cron runner script loads `modules.yaml`, filters by tier, and runs each
enabled module in sequence:

```bash
# Quick tier (15-min cron)
python3 {baseDir}/scripts/metacog-runner.py --tier quick

# Deep tier (1-hour cron)
python3 {baseDir}/scripts/metacog-runner.py --tier deep

# Run a specific module only
python3 {baseDir}/scripts/metacog-runner.py --module conflict-resolution

# Dry run (show what would execute)
python3 {baseDir}/scripts/metacog-runner.py --tier deep --dry-run
```

### Manual (ad-hoc)

Run any module directly:

```bash
python3 {baseDir}/scripts/modules/conflict-resolution.py
python3 {baseDir}/scripts/modules/session-analyzer.py --days 3
```

## Module Contract

Every module is a Python script that:

1. Accepts `--output-dir <path>` for where to write findings
2. Prints structured output to stdout (for the runner to capture)
3. Returns exit code 0 (ok), 1 (findings), 2 (error)
4. Writes detailed findings to `output/YYYY-MM-DD.md` (append)

```python
#!/usr/bin/env python3
"""Module: <name> — <one-line description>"""

import argparse, sys
from datetime import datetime
from pathlib import Path

def run(output_dir: Path) -> int:
    """Run the module. Return 0=ok, 1=findings, 2=error."""
    findings = []
    # ... do analysis ...
    
    if findings:
        # Append to daily log
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — <Module Name>\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        return 1
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, 
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    args = parser.parse_args()
    sys.exit(run(args.output_dir))
```

## Conflict Resolution Module

The most complex module. See `{baseDir}/references/conflict-resolution.md` for:

- Full resolution process (detect → research → document → decide → apply)
- CR document template
- Gate integration with openclaw-gates
- Self-resolvable vs escalation criteria

## Enforcement via openclaw-gates

This skill requires the `openclaw-gates` Plugin SDK plugin for enforcement.

The openclaw-gates plugin can enforce conflict resolution via `before_tool_call`:
when a build action conflicts with existing lessons, the gate blocks until a CR
document exists. See `{baseDir}/references/gate-integration.md`.

### Why openclaw-gates (not managed hooks)

Per lesson 002 (`memory/lessons/002-managed-vs-plugin-hooks.md`):
- Managed hooks can only observe — they cannot block tool calls
- Plugin SDK hooks support `before_tool_call` with blocking
- Enforcement MUST use Plugin SDK hooks

## Adding a New Module

1. Create `{baseDir}/scripts/modules/<name>.py` following the module contract
2. Add entry to `modules.yaml` with `enabled`, `tier`, and `description`
3. Test: `python3 {baseDir}/scripts/metacog-runner.py --module <name> --dry-run`
4. Enable in production by setting `enabled: true`

## Migration from Existing System

The skill includes a safe migration tool that replaces ad-hoc metacognition cron
jobs with the modular system. The migration follows: analyze → backup → plan →
present → execute → monitor.

### Migration Commands

```bash
# Analyze current environment, produce migration document
python3 {baseDir}/scripts/migrate.py analyze

# Date-stamped backup of all affected files
python3 {baseDir}/scripts/migrate.py backup

# Execute the migration plan
python3 {baseDir}/scripts/migrate.py execute

# Post-migration health check
python3 {baseDir}/scripts/migrate.py verify

# Restore from backup if needed
python3 {baseDir}/scripts/migrate.py rollback

# Full pipeline (analyze → backup → execute → verify)
python3 {baseDir}/scripts/migrate.py full

# Preview without changing anything
python3 {baseDir}/scripts/migrate.py dry-run
```

### What the migration does

1. **Analyze** — scans existing cron jobs, old metacog files, tests new modules,
   runs dry runs of both tiers, identifies blockers/warnings, documents benefits.
   Writes analysis to `analyses/migration-analysis-YYYYMMDD-HHMMSS.md`.

2. **Backup** — date-stamped copy of all affected files to
   `.archive/metacog-migration-YYYYMMDDTHHMMSS/`. Includes old scripts, cron job
   configs (JSON export), and existing metacognition output. Never deletes anything.

3. **Execute** — disables old `self-audit` cron, creates `metacog-quick` (15m,
   Haiku) and `metacog-deep` (1h, Sonnet) crons pointing to the runner, archives
   old scripts to `.archive/`.

4. **Verify** — confirms new crons exist and are enabled, old cron is disabled,
   both tiers run successfully, non-migration crons are untouched.

### What is NOT migrated

These cron jobs are not metacognition and are left untouched:
- `schedule-briefing`, `session-health`, `claude-tab-monitor`
- `slack-missed-detector`, `trello-work`
- `Memory Dreaming Promotion`, `daily-squad-scheduler`

### Rollback

If anything goes wrong, `migrate.py rollback` restores from the most recent
backup: re-enables old cron, removes new crons, restores archived scripts.

## Output & Reporting

- Daily logs: `memory/metacognition/YYYY-MM-DD.md`
- Conflict resolutions: `memory/conflict-resolutions/CR-NNN-slug.md`
- Migration analyses: `{baseDir}/analyses/migration-analysis-*.md`
- Post actionable findings to `#coco-metacognition` (Slack C0ATCRVSB71)
- Stay silent when nothing meaningful to report
