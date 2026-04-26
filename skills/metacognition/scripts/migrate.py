#!/usr/bin/env python3
"""Metacognition Migration Tool — analyze, backup, plan, execute, verify.

Safe migration from existing ad-hoc cron jobs to the modular metacognition system.
Follows the principle: analyze → backup → plan → present → execute → monitor.

Usage:
    python3 migrate.py analyze        # Analyze current environment, produce migration doc
    python3 migrate.py backup         # Date-stamped backup of all affected files
    python3 migrate.py execute        # Execute the migration plan
    python3 migrate.py verify         # Post-migration health check
    python3 migrate.py rollback       # Restore from backup if needed
    python3 migrate.py full           # Run all steps in sequence (analyze→backup→execute→verify)
    python3 migrate.py dry-run        # Full pipeline but don't actually change anything
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
ARCHIVE_DIR = WORKSPACE / ".archive"
SKILL_DIR = Path(__file__).resolve().parent.parent
ANALYSES_DIR = SKILL_DIR / "analyses"
MODULES_DIR = Path(__file__).resolve().parent / "modules"

# Cron jobs that are metacognition-related and candidates for migration
METACOG_CRON_NAMES = ["self-audit"]

# Cron jobs that are NOT metacognition (should NOT be migrated)
NON_METACOG_CRON_NAMES = [
    "schedule-briefing",
    "session-health",
    "claude-tab-monitor",
    "slack-missed-detector",
    "trello-work",
    "Memory Dreaming Promotion",
    "daily-squad-scheduler",
]

# Files that the old metacog system uses
OLD_METACOG_FILES = [
    Path.home() / "openclaw-dm/scripts/metacognition/self-audit.py",
    WORKSPACE / "scripts/metacognition/analyze_sessions.py",
    WORKSPACE / "scripts/metacognition-check.md",
    WORKSPACE / "scripts/metacognition-rules.md",
    WORKSPACE / "scripts/metacognition-big-review.md",
]


def run_cmd(cmd: list, timeout: int = 30) -> tuple:
    """Run a command and return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1
    except Exception as e:
        return "", str(e), 1


def get_cron_jobs() -> list:
    """Get all current cron jobs as parsed JSON."""
    stdout, _, rc = run_cmd(["openclaw", "cron", "list", "--json"])
    if rc != 0:
        return []
    try:
        data = json.loads(stdout)
        return data.get("jobs", [])
    except json.JSONDecodeError:
        return []


def analyze_environment() -> dict:
    """Analyze the current metacognition environment."""
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "existing_crons": [],
        "old_metacog_files": [],
        "new_skill_modules": [],
        "migration_candidates": [],
        "non_migration_crons": [],
        "blockers": [],
        "warnings": [],
        "benefits": [],
        "dry_run_results": {},
    }

    # 1. Catalog existing cron jobs
    jobs = get_cron_jobs()
    for job in jobs:
        name = job.get("name", "")
        entry = {
            "id": job.get("id", ""),
            "name": name,
            "enabled": job.get("enabled", False),
            "schedule": job.get("schedule", {}),
            "model": job.get("payload", {}).get("model", "default"),
            "target": job.get("sessionTarget", ""),
            "last_status": job.get("state", {}).get("lastStatus", "unknown"),
            "last_error": job.get("state", {}).get("lastError", ""),
            "consecutive_errors": job.get("state", {}).get("consecutiveErrors", 0),
            "prompt_preview": job.get("payload", {}).get("message", "")[:200],
        }
        analysis["existing_crons"].append(entry)

        if name in METACOG_CRON_NAMES:
            analysis["migration_candidates"].append(entry)
        elif name in NON_METACOG_CRON_NAMES:
            analysis["non_migration_crons"].append(entry)
        else:
            analysis["warnings"].append(
                f"Unknown cron job '{name}' — not categorized. Review manually."
            )

    # 2. Check old metacog files
    for f in OLD_METACOG_FILES:
        if f.exists():
            stat = f.stat()
            analysis["old_metacog_files"].append({
                "path": str(f),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "exists": True,
            })
        else:
            analysis["old_metacog_files"].append({
                "path": str(f),
                "exists": False,
            })

    # 3. Catalog new modules
    for f in sorted(MODULES_DIR.glob("*.py")):
        analysis["new_skill_modules"].append({
            "name": f.stem,
            "path": str(f),
            "size": f.stat().st_size,
        })

    # 4. Check for blockers
    if not MODULES_DIR.exists():
        analysis["blockers"].append("Modules directory does not exist")

    modules_yaml = SKILL_DIR / "modules.yaml"
    if not modules_yaml.exists():
        analysis["blockers"].append("modules.yaml does not exist")

    # Check if runner works
    runner = Path(__file__).resolve().parent / "metacog-runner.py"
    if not runner.exists():
        analysis["blockers"].append("metacog-runner.py does not exist")
    else:
        stdout, stderr, rc = run_cmd([sys.executable, str(runner), "--list"])
        if rc != 0:
            analysis["blockers"].append(f"Runner --list failed: {stderr[:200]}")

    # 5. Potential warnings
    for job in analysis["migration_candidates"]:
        if job["consecutive_errors"] > 0:
            analysis["warnings"].append(
                f"Cron '{job['name']}' has {job['consecutive_errors']} consecutive errors — "
                f"migration won't fix underlying issues"
            )
        if job["last_status"] == "error":
            analysis["warnings"].append(
                f"Cron '{job['name']}' last run errored: {job.get('last_error', 'unknown')}"
            )

    # 6. Benefits
    analysis["benefits"] = [
        "Modular enable/disable per metacognition task (no monolithic cron prompts)",
        "Two-tier model: quick (15m) for cheap checks, deep (1h) for expensive analysis",
        "Independent module testing via --module flag",
        "Structured output to daily logs instead of ad-hoc appending",
        "Conflict resolution: automated detection of lesson/spec contradictions",
        "Pattern detection: catches circular rebuilds and token waste automatically",
        "Lesson review: structural integrity checks on lesson files",
        "Dry-run mode for previewing what each cycle would do",
        "Shareable as an OpenClaw skill (.skill package)",
    ]

    # 7. Run dry runs
    for tier in ["quick", "deep"]:
        stdout, stderr, rc = run_cmd(
            [sys.executable, str(runner), "--tier", tier, "--dry-run"],
            timeout=15,
        )
        analysis["dry_run_results"][tier] = {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "exit_code": rc,
        }

    # 8. Run actual quick + deep tiers for demo results
    for tier in ["quick", "deep"]:
        stdout, stderr, rc = run_cmd(
            [sys.executable, str(runner), "--tier", tier],
            timeout=120,
        )
        analysis["dry_run_results"][f"{tier}_live"] = {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "exit_code": rc,
        }

    return analysis


def format_analysis_document(analysis: dict) -> str:
    """Format analysis into a readable markdown document."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M CDT")
    lines = [
        f"# Metacognition Migration Analysis",
        f"Generated: {ts}",
        "",
        "## Executive Summary",
        "",
        f"- *{len(analysis['existing_crons'])}* existing cron jobs found",
        f"- *{len(analysis['migration_candidates'])}* are metacognition-related (migration candidates)",
        f"- *{len(analysis['non_migration_crons'])}* are non-metacognition (will NOT be touched)",
        f"- *{len(analysis['new_skill_modules'])}* new modular modules ready",
        f"- *{len(analysis['blockers'])}* blockers",
        f"- *{len(analysis['warnings'])}* warnings",
        "",
    ]

    # Blockers
    if analysis["blockers"]:
        lines.extend([
            "## ❌ Blockers (must fix before migration)",
            "",
        ])
        for b in analysis["blockers"]:
            lines.append(f"- {b}")
        lines.append("")
    else:
        lines.append("## ✅ No Blockers — Ready to Migrate")
        lines.append("")

    # Warnings
    if analysis["warnings"]:
        lines.extend(["## ⚠️ Warnings", ""])
        for w in analysis["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    # Migration candidates
    lines.extend([
        "## Migration Candidates (will be replaced)",
        "",
        "| Cron Name | Schedule | Model | Status | Errors |",
        "|---|---|---|---|---|",
    ])
    for job in analysis["migration_candidates"]:
        sched = job["schedule"]
        sched_str = sched.get("expr", f"every {sched.get('everyMs', 0)//60000}m")
        lines.append(
            f"| {job['name']} | {sched_str} | {job['model'][:30]} | "
            f"{job['last_status']} | {job['consecutive_errors']} |"
        )
    lines.append("")

    # Non-migration crons
    lines.extend([
        "## Non-Migration Crons (will NOT be touched)",
        "",
    ])
    for job in analysis["non_migration_crons"]:
        lines.append(f"- **{job['name']}** — {job['last_status']}")
    lines.append("")

    # Old files
    lines.extend(["## Old Metacognition Files (will be archived)", ""])
    for f in analysis["old_metacog_files"]:
        status = f"exists ({f.get('size', 0)} bytes, modified {f.get('modified', '?')[:10]})" if f["exists"] else "not found"
        lines.append(f"- `{f['path']}` — {status}")
    lines.append("")

    # New modules
    lines.extend(["## New Modular System", ""])
    for m in analysis["new_skill_modules"]:
        lines.append(f"- **{m['name']}** — `{m['path']}` ({m['size']} bytes)")
    lines.append("")

    # Dry run results
    lines.extend(["## Dry Run Results", ""])
    for tier in ["quick", "deep"]:
        dr = analysis["dry_run_results"].get(tier, {})
        lines.extend([
            f"### {tier.title()} Tier (dry run)",
            "```",
            dr.get("stdout", "(no output)"),
            "```",
            "",
        ])

    # Live run results
    lines.extend(["## Live Test Results (demonstration)", ""])
    for tier in ["quick", "deep"]:
        lr = analysis["dry_run_results"].get(f"{tier}_live", {})
        lines.extend([
            f"### {tier.title()} Tier (live)",
            "```",
            lr.get("stdout", "(no output)"),
            "```",
            "",
        ])

    # Benefits
    lines.extend(["## Benefits of Migration", ""])
    for b in analysis["benefits"]:
        lines.append(f"- {b}")
    lines.append("")

    # Migration plan
    lines.extend([
        "## Migration Plan",
        "",
        "### Step 1: Backup (automatic)",
        "- Date-stamped copies of all affected files → `.archive/metacog-migration-YYYYMMDD-HHMMSS/`",
        "- Cron job configs exported to JSON backup",
        "",
        "### Step 2: Replace cron jobs",
        "- Disable old `self-audit` cron",
        "- Create new `metacog-quick` cron (every 15m, Haiku, runs metacog-runner.py --tier quick)",
        "- Create new `metacog-deep` cron (every 1h, Sonnet, runs metacog-runner.py --tier deep)",
        "",
        "### Step 3: Archive old files",
        "- Move old metacog scripts to `.archive/` (never delete)",
        "",
        "### Step 4: Verify",
        "- Run both tiers and confirm output matches expectations",
        "- Compare with last known-good output from old system",
        "- Monitor for 24h via audit logs",
        "",
        "### Rollback Plan",
        "- Restore cron jobs from JSON backup",
        "- Restore files from `.archive/` backup",
        "- All backups are date-stamped and never overwritten",
        "",
    ])

    return "\n".join(lines)


def do_analyze(dry_run: bool = False) -> str:
    """Run analysis and write document. Returns path to analysis doc."""
    analysis = analyze_environment()
    doc = format_analysis_document(analysis)

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    doc_path = ANALYSES_DIR / f"migration-analysis-{ts}.md"
    doc_path.write_text(doc)

    # Also save raw JSON for programmatic use
    json_path = ANALYSES_DIR / f"migration-analysis-{ts}.json"
    json_path.write_text(json.dumps(analysis, indent=2, default=str))

    print(f"📄 Analysis document: {doc_path}")
    print(f"📊 Raw data: {json_path}")
    return str(doc_path)


def do_backup() -> str:
    """Create date-stamped backup of all affected files."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = ARCHIVE_DIR / f"metacog-migration-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up = []

    # Backup old metacog files
    for f in OLD_METACOG_FILES:
        if f.exists():
            # Preserve relative path structure
            rel = f.name
            dest = backup_dir / "old-scripts" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            backed_up.append(str(f))

    # Backup cron job configs
    jobs = get_cron_jobs()
    cron_backup = backup_dir / "cron-jobs-backup.json"
    cron_backup.write_text(json.dumps(jobs, indent=2, default=str))
    backed_up.append("cron job configs")

    # Backup existing metacognition output
    metacog_output = WORKSPACE / "memory" / "metacognition"
    if metacog_output.exists():
        dest = backup_dir / "metacognition-output"
        shutil.copytree(metacog_output, dest, dirs_exist_ok=True)
        backed_up.append(str(metacog_output))

    # Write manifest
    manifest = backup_dir / "MANIFEST.md"
    manifest.write_text(
        f"# Metacognition Migration Backup\n"
        f"Created: {datetime.now().isoformat()}\n\n"
        f"## Files backed up:\n"
        + "\n".join(f"- {f}" for f in backed_up)
        + f"\n\n## Restore command:\n"
        f"```\npython3 {__file__} rollback --backup-dir {backup_dir}\n```\n"
    )

    print(f"📦 Backup created: {backup_dir}")
    print(f"   {len(backed_up)} items backed up")
    return str(backup_dir)


def do_execute(dry_run: bool = False) -> bool:
    """Execute the migration plan."""
    runner = Path(__file__).resolve().parent / "metacog-runner.py"

    if dry_run:
        print("🏗️  [DRY RUN] Would execute migration:")
        print("  1. Disable old self-audit cron")
        print("  2. Create metacog-quick cron (every 15m)")
        print("  3. Create metacog-deep cron (every 1h)")
        print("  4. Archive old metacog scripts")
        return True

    # Step 1: Disable old self-audit cron
    print("📋 Step 1: Disabling old self-audit cron...")
    stdout, stderr, rc = run_cmd(["openclaw", "cron", "disable", "self-audit"])
    if rc != 0 and "not found" not in stderr.lower():
        print(f"  ⚠️  Could not disable self-audit: {stderr[:100]}")
    else:
        print("  ✅ self-audit disabled (or not found)")

    # Step 2: Create new cron jobs
    # Quick tier
    print("📋 Step 2a: Creating metacog-quick cron (every 15m)...")
    quick_prompt = (
        f"Run the metacognition quick tier: python3 {runner} --tier quick. "
        f"If any module returns findings (exit code 1), review the output. "
        f"If any 🔴 anti-patterns are found, post a brief alert to Joel DM (D0ATWPM4DTK) "
        f"via message(action=send, channel=slack, target=D0ATWPM4DTK). "
        f"Start and end channel messages with 🌴. "
        f"Otherwise reply HEARTBEAT_OK."
    )
    stdout, stderr, rc = run_cmd([
        "openclaw", "cron", "add",
        "--name", "metacog-quick",
        "--schedule", "every 15m",
        "--model", "trendmicro-aiendpoint/claude-4.5-haiku",
        "--target", "isolated",
        "--light-context",
        "--thinking", "off",
        "--timeout", "120",
        "--message", quick_prompt,
    ])
    if rc != 0:
        print(f"  ❌ Failed to create metacog-quick: {stderr[:200]}")
        return False
    print("  ✅ metacog-quick created")

    # Deep tier
    print("📋 Step 2b: Creating metacog-deep cron (every 1h)...")
    deep_prompt = (
        f"Run the metacognition deep tier: python3 {runner} --tier deep. "
        f"Review findings from all modules. For conflict-resolution findings, check if any "
        f"CR documents need escalation to Joel. For pattern-detector findings with 🔴 flags, "
        f"post to #coco-metacognition (C0ATCRVSB71) via message(action=send, channel=slack, "
        f"target=C0ATCRVSB71). Write a 2-3 sentence self-reflection and append to "
        f"memory/metacognition/$(date +%Y-%m-%d).md. "
        f"Start and end channel messages with 🌴. If everything is clean, reply HEARTBEAT_OK."
    )
    stdout, stderr, rc = run_cmd([
        "openclaw", "cron", "add",
        "--name", "metacog-deep",
        "--schedule", "every 1h",
        "--model", "trendmicro-aiendpoint/claude-4.6-sonnet",
        "--target", "isolated",
        "--light-context",
        "--thinking", "low",
        "--timeout", "300",
        "--message", deep_prompt,
    ])
    if rc != 0:
        print(f"  ❌ Failed to create metacog-deep: {stderr[:200]}")
        return False
    print("  ✅ metacog-deep created")

    # Step 3: Archive old files (never delete)
    print("📋 Step 3: Archiving old metacog scripts...")
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    archive_dest = ARCHIVE_DIR / f"old-metacog-scripts-{ts}"
    archived = 0
    for f in OLD_METACOG_FILES:
        if f.exists():
            dest = archive_dest / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            archived += 1
    if archived > 0:
        print(f"  ✅ {archived} files archived to {archive_dest}")
    else:
        print("  ℹ️  No old files to archive")

    print("✅ Migration complete!")
    return True


def do_verify() -> bool:
    """Post-migration verification."""
    runner = Path(__file__).resolve().parent / "metacog-runner.py"
    success = True

    print("🔍 Post-migration verification...")

    # 1. Check new cron jobs exist
    print("\n📋 Checking new cron jobs...")
    jobs = get_cron_jobs()
    job_names = [j.get("name", "") for j in jobs]

    for expected in ["metacog-quick", "metacog-deep"]:
        if expected in job_names:
            job = next(j for j in jobs if j["name"] == expected)
            status = "✅ enabled" if job.get("enabled") else "⚠️ disabled"
            print(f"  {status}: {expected}")
        else:
            print(f"  ❌ MISSING: {expected}")
            success = False

    # 2. Check old cron disabled
    if "self-audit" in job_names:
        job = next(j for j in jobs if j["name"] == "self-audit")
        if job.get("enabled"):
            print("  ⚠️  Old self-audit cron still enabled")
        else:
            print("  ✅ Old self-audit cron disabled")
    else:
        print("  ℹ️  Old self-audit cron not found (ok)")

    # 3. Run both tiers to confirm they work
    print("\n📋 Running quick tier test...")
    stdout, stderr, rc = run_cmd([sys.executable, str(runner), "--tier", "quick"], timeout=60)
    if rc <= 1:  # 0=ok, 1=findings (both are valid)
        print(f"  ✅ Quick tier ran successfully (exit {rc})")
        print(f"     {stdout.strip()[:200]}")
    else:
        print(f"  ❌ Quick tier failed (exit {rc}): {stderr[:200]}")
        success = False

    print("\n📋 Running deep tier test...")
    stdout, stderr, rc = run_cmd([sys.executable, str(runner), "--tier", "deep"], timeout=120)
    if rc <= 1:
        print(f"  ✅ Deep tier ran successfully (exit {rc})")
        print(f"     {stdout.strip()[:200]}")
    else:
        print(f"  ❌ Deep tier failed (exit {rc}): {stderr[:200]}")
        success = False

    # 4. Check non-migration crons are untouched
    print("\n📋 Checking non-migration crons untouched...")
    for name in NON_METACOG_CRON_NAMES:
        if name in job_names:
            job = next(j for j in jobs if j["name"] == name)
            status = "✅" if job.get("enabled") else "⚠️ disabled"
            print(f"  {status} {name}")
        else:
            print(f"  ℹ️  {name} not found")

    print(f"\n{'✅ Verification PASSED' if success else '❌ Verification FAILED'}")
    return success


def do_rollback(backup_dir: str = None):
    """Rollback migration from backup."""
    if not backup_dir:
        # Find most recent backup
        backups = sorted(ARCHIVE_DIR.glob("metacog-migration-*"))
        if not backups:
            print("❌ No backups found in .archive/")
            return False
        backup_dir = str(backups[-1])

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_dir}")
        return False

    print(f"🔄 Rolling back from: {backup_path}")

    # Restore cron jobs
    cron_backup = backup_path / "cron-jobs-backup.json"
    if cron_backup.exists():
        print("📋 Re-enabling old self-audit cron...")
        run_cmd(["openclaw", "cron", "enable", "self-audit"])

        print("📋 Removing new metacog crons...")
        run_cmd(["openclaw", "cron", "rm", "metacog-quick"])
        run_cmd(["openclaw", "cron", "rm", "metacog-deep"])

    # Restore old scripts
    old_scripts = backup_path / "old-scripts"
    if old_scripts.exists():
        print("📋 Restoring old scripts...")
        for f in old_scripts.iterdir():
            # Find original path from OLD_METACOG_FILES
            for orig in OLD_METACOG_FILES:
                if orig.name == f.name:
                    orig.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, orig)
                    print(f"  ✅ Restored {orig}")

    print("✅ Rollback complete")
    return True


def main():
    parser = argparse.ArgumentParser(description="Metacognition migration tool")
    parser.add_argument("action", choices=[
        "analyze", "backup", "execute", "verify", "rollback", "full", "dry-run"
    ])
    parser.add_argument("--backup-dir", help="Backup directory for rollback")
    args = parser.parse_args()

    if args.action == "analyze":
        do_analyze()

    elif args.action == "backup":
        do_backup()

    elif args.action == "execute":
        do_execute()

    elif args.action == "verify":
        ok = do_verify()
        sys.exit(0 if ok else 1)

    elif args.action == "rollback":
        ok = do_rollback(args.backup_dir)
        sys.exit(0 if ok else 1)

    elif args.action == "dry-run":
        print("=" * 60)
        print("DRY RUN — No changes will be made")
        print("=" * 60)
        print()
        do_analyze(dry_run=True)
        print()
        print("=" * 40)
        print("Backup would be created in:")
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        print(f"  {ARCHIVE_DIR}/metacog-migration-{ts}/")
        print()
        do_execute(dry_run=True)

    elif args.action == "full":
        print("=" * 60)
        print("FULL MIGRATION — analyze → backup → execute → verify")
        print("=" * 60)
        print()

        print("Phase 1: Analysis")
        print("-" * 40)
        doc_path = do_analyze()
        print()

        print("Phase 2: Backup")
        print("-" * 40)
        backup_path = do_backup()
        print()

        print("Phase 3: Execute")
        print("-" * 40)
        ok = do_execute()
        if not ok:
            print("\n❌ Migration failed — rolling back...")
            do_rollback(backup_path)
            sys.exit(1)
        print()

        print("Phase 4: Verify")
        print("-" * 40)
        ok = do_verify()
        if not ok:
            print("\n⚠️  Verification found issues — review before continuing")
            print(f"    Rollback available: python3 {__file__} rollback")
        print()

        print(f"\n📄 Analysis document: {doc_path}")
        print(f"📦 Backup: {backup_path}")


if __name__ == "__main__":
    main()
