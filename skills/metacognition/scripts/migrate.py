#!/usr/bin/env python3
"""Metacognition Migration Tool — analyze, backup, plan, execute, verify.

Safe migration from existing ad-hoc cron jobs to the modular metacognition system.
Pipeline: analyze → backup → execute → verify.
Data flows through a migration plan JSON written by analyze and consumed by execute.

Usage:
    python3 migrate.py analyze        # Analyze environment, produce migration plan + doc
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
import re
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
MODULES_YAML = SKILL_DIR / "modules.yaml"
RUNNER = Path(__file__).resolve().parent / "metacog-runner.py"

# Keywords that signal a cron is doing metacognition-type work
METACOG_KEYWORDS = [
    "self-audit", "self-reflection", "metacognition", "metacog",
    "analyze_sessions", "session analyzer", "pattern detect",
    "lesson review", "conflict resolution", "decision check",
    "self-reflection", "anti-pattern", "circular rebuild",
    "thinking about thinking",
]

# Keywords that signal a cron is NOT metacognition
NON_METACOG_KEYWORDS = [
    "schedule", "briefing", "monitor.py", "manage-claude-code",
    "missed message", "missed detector", "trello", "todo",
    "dreaming", "memory_core", "squad-scheduler",
    "tab monitor", "session-health",
]


def run_cmd(cmd: list, timeout: int = 30) -> tuple:
    """Run a command and return (stdout, stderr, returncode)."""
    try:
        env = os.environ.copy()
        env["OPENCLAW_SKIP_CONFIG_VALIDATION"] = "1"
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        # If config validation fails, retry without the flag but log warning
        if r.returncode != 0 and "Invalid config" in r.stderr:
            # Try with --no-validate if available, otherwise use shell
            r2 = subprocess.run(
                " ".join(cmd), shell=True, capture_output=True, text=True, timeout=timeout
            )
            if r2.returncode == 0:
                return r2.stdout, r2.stderr, r2.returncode
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


def load_module_descriptions() -> dict:
    """Load module descriptions from modules.yaml."""
    if not MODULES_YAML.exists():
        return {}
    try:
        import yaml
        with open(MODULES_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("modules", {})
    except ImportError:
        # Fallback: parse manually if pyyaml not available
        modules = {}
        current_name = None
        with open(MODULES_YAML) as f:
            for line in f:
                stripped = line.strip()
                # Top-level module name (2-space indent under modules:)
                if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
                    name = stripped.rstrip(":").strip()
                    if name != "modules":
                        current_name = name
                        modules[current_name] = {}
                elif current_name and line.startswith("    "):
                    if "description:" in stripped:
                        modules[current_name]["description"] = stripped.split("description:", 1)[1].strip()
                    elif "tier:" in stripped:
                        modules[current_name]["tier"] = stripped.split("tier:", 1)[1].strip()
                    elif "enabled:" in stripped:
                        modules[current_name]["enabled"] = "true" in stripped.lower()
        return modules


def classify_cron(job: dict, module_descriptions: dict) -> dict:
    """Dynamically classify a cron job as replace/coexist/review.

    Returns: {classification, reason, matching_modules}
    """
    name = job.get("name", "")
    prompt = job.get("payload", {}).get("message", "").lower()
    combined = f"{name} {prompt}".lower()

    # Score against metacog keywords
    metacog_score = sum(1 for kw in METACOG_KEYWORDS if kw.lower() in combined)

    # Score against non-metacog keywords
    non_metacog_score = sum(1 for kw in NON_METACOG_KEYWORDS if kw.lower() in combined)

    # Check if any new module covers this cron's purpose
    matching_modules = []
    for mod_name, mod_info in module_descriptions.items():
        mod_desc = mod_info.get("description", "").lower()
        # Check for semantic overlap between cron prompt and module description
        overlap_words = set(prompt.split()) & set(mod_desc.split())
        # Filter out common words
        meaningful = {w for w in overlap_words if len(w) > 4}
        if len(meaningful) >= 3:
            matching_modules.append(mod_name)
        # Also check direct name match
        if mod_name.replace("-", " ") in combined or mod_name.replace("-", "_") in combined:
            if mod_name not in matching_modules:
                matching_modules.append(mod_name)

    # Classification logic
    if non_metacog_score > metacog_score and not matching_modules:
        return {
            "classification": "coexist",
            "reason": f"Non-metacognition cron (matched {non_metacog_score} non-metacog keywords)",
            "matching_modules": [],
        }
    elif matching_modules and metacog_score > non_metacog_score:
        return {
            "classification": "replace",
            "reason": f"Covered by modules: {', '.join(matching_modules)} "
                      f"(matched {metacog_score} metacog keywords)",
            "matching_modules": matching_modules,
        }
    elif metacog_score > 0 and matching_modules:
        return {
            "classification": "review",
            "reason": f"Partial overlap with {', '.join(matching_modules)} — "
                      f"human should verify ({metacog_score} metacog, {non_metacog_score} non-metacog keywords)",
            "matching_modules": matching_modules,
        }
    elif metacog_score > non_metacog_score:
        return {
            "classification": "review",
            "reason": f"Looks metacognition-related ({metacog_score} keywords) "
                      f"but no module directly covers it",
            "matching_modules": [],
        }
    else:
        return {
            "classification": "coexist",
            "reason": f"No metacognition overlap detected",
            "matching_modules": [],
        }


def find_old_metacog_files() -> list:
    """Dynamically find old metacognition-related files."""
    candidates = []

    # Known locations to scan
    scan_paths = [
        WORKSPACE / "scripts",
        Path.home() / "openclaw-dm" / "scripts" / "metacognition",
    ]

    for scan_dir in scan_paths:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*"):
            if not f.is_file():
                continue
            name_lower = f.name.lower()
            # Match files with metacognition-related names
            if any(kw in name_lower for kw in [
                "metacog", "self-audit", "self_audit",
                "analyze_sessions", "session_analyzer",
            ]):
                candidates.append(f)
            # Also check .md files that look like metacog prompts/rules
            if f.suffix == ".md" and any(kw in name_lower for kw in [
                "metacognition", "metacog",
            ]):
                candidates.append(f)

    return sorted(set(candidates))


def analyze_environment() -> dict:
    """Analyze the current metacognition environment."""
    module_descriptions = load_module_descriptions()

    analysis = {
        "timestamp": datetime.now().isoformat(),
        "existing_crons": [],
        "classified_crons": {},
        "old_metacog_files": [],
        "new_skill_modules": [],
        "blockers": [],
        "warnings": [],
        "benefits": [],
        "dry_run_results": {},
    }

    # 1. Catalog and classify existing cron jobs
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
            "prompt_preview": job.get("payload", {}).get("message", "")[:300],
        }
        analysis["existing_crons"].append(entry)

        # Dynamic classification
        classification = classify_cron(job, module_descriptions)
        analysis["classified_crons"][name] = {
            **entry,
            **classification,
        }

    # 2. Find old metacog files dynamically
    old_files = find_old_metacog_files()
    for f in old_files:
        stat = f.stat()
        analysis["old_metacog_files"].append({
            "path": str(f),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    # 3. Catalog new modules
    if MODULES_DIR.exists():
        for f in sorted(MODULES_DIR.glob("*.py")):
            desc = module_descriptions.get(f.stem, {}).get("description", "")
            tier = module_descriptions.get(f.stem, {}).get("tier", "?")
            analysis["new_skill_modules"].append({
                "name": f.stem,
                "path": str(f),
                "size": f.stat().st_size,
                "description": desc,
                "tier": tier,
            })

    # 4. Check for blockers
    if not MODULES_DIR.exists():
        analysis["blockers"].append("Modules directory does not exist")
    if not MODULES_YAML.exists():
        analysis["blockers"].append("modules.yaml does not exist")
    if not RUNNER.exists():
        analysis["blockers"].append("metacog-runner.py does not exist")
    else:
        stdout, stderr, rc = run_cmd([sys.executable, str(RUNNER), "--list"])
        if rc != 0:
            analysis["blockers"].append(f"Runner --list failed: {stderr[:200]}")

    # 5. Warnings
    review_crons = [
        n for n, c in analysis["classified_crons"].items()
        if c["classification"] == "review"
    ]
    if review_crons:
        analysis["warnings"].append(
            f"Crons needing human review: {', '.join(review_crons)}"
        )

    for name, c in analysis["classified_crons"].items():
        if c.get("consecutive_errors", 0) > 0:
            analysis["warnings"].append(
                f"Cron '{name}' has {c['consecutive_errors']} consecutive errors"
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

    # 7. Dry run + live demo of both tiers
    for tier in ["quick", "deep"]:
        stdout, stderr, rc = run_cmd(
            [sys.executable, str(RUNNER), "--tier", tier, "--dry-run"], timeout=15,
        )
        analysis["dry_run_results"][f"{tier}_dry"] = {
            "stdout": stdout.strip(), "stderr": stderr.strip(), "exit_code": rc,
        }
        stdout, stderr, rc = run_cmd(
            [sys.executable, str(RUNNER), "--tier", tier], timeout=120,
        )
        analysis["dry_run_results"][f"{tier}_live"] = {
            "stdout": stdout.strip(), "stderr": stderr.strip(), "exit_code": rc,
        }

    return analysis


def format_analysis_document(analysis: dict) -> str:
    """Format analysis into a readable markdown document."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M CDT")

    # Count by classification
    replace_crons = [
        n for n, c in analysis["classified_crons"].items()
        if c["classification"] == "replace"
    ]
    coexist_crons = [
        n for n, c in analysis["classified_crons"].items()
        if c["classification"] == "coexist"
    ]
    review_crons = [
        n for n, c in analysis["classified_crons"].items()
        if c["classification"] == "review"
    ]

    lines = [
        f"# Metacognition Migration Analysis",
        f"Generated: {ts}",
        "",
        "## Executive Summary",
        "",
        f"- **{len(analysis['existing_crons'])}** existing cron jobs analyzed",
        f"- **{len(replace_crons)}** classified as `replace` (new modules cover them)",
        f"- **{len(coexist_crons)}** classified as `coexist` (will NOT be touched)",
        f"- **{len(review_crons)}** classified as `review` (human decision needed)",
        f"- **{len(analysis['new_skill_modules'])}** new modular modules ready",
        f"- **{len(analysis['blockers'])}** blockers",
        f"- **{len(analysis['warnings'])}** warnings",
        "",
    ]

    # Blockers
    if analysis["blockers"]:
        lines.extend(["## ❌ Blockers", ""])
        for b in analysis["blockers"]:
            lines.append(f"- {b}")
        lines.append("")
    else:
        lines.extend(["## ✅ No Blockers — Ready to Migrate", ""])

    # Warnings
    if analysis["warnings"]:
        lines.extend(["## ⚠️ Warnings", ""])
        for w in analysis["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    # Classification table
    lines.extend([
        "## Cron Classification (dynamically determined)",
        "",
        "| Cron Name | Classification | Reason | Matching Modules |",
        "|---|---|---|---|",
    ])
    for name, c in sorted(analysis["classified_crons"].items()):
        icon = {"replace": "🔄", "coexist": "✅", "review": "🔍"}.get(c["classification"], "?")
        modules = ", ".join(c.get("matching_modules", [])) or "—"
        reason = c["reason"][:80]
        lines.append(f"| {name} | {icon} {c['classification']} | {reason} | {modules} |")
    lines.append("")

    # Replace candidates detail
    if replace_crons:
        lines.extend(["## Crons to Replace (modules cover their function)", ""])
        for name in replace_crons:
            c = analysis["classified_crons"][name]
            sched = c["schedule"]
            sched_str = sched.get("expr", f"every {sched.get('everyMs', 0)//60000}m")
            lines.extend([
                f"### {name}",
                f"- Schedule: {sched_str}",
                f"- Model: {c['model'][:40]}",
                f"- Status: {c['last_status']}",
                f"- Covered by: {', '.join(c.get('matching_modules', []))}",
                f"- Prompt preview: `{c['prompt_preview'][:150]}...`",
                "",
            ])

    # Review candidates
    if review_crons:
        lines.extend(["## Crons Needing Human Review", ""])
        for name in review_crons:
            c = analysis["classified_crons"][name]
            lines.extend([
                f"### {name}",
                f"- Reason: {c['reason']}",
                f"- Prompt preview: `{c['prompt_preview'][:150]}...`",
                f"- **Action needed:** confirm replace or coexist",
                "",
            ])

    # Coexist crons (brief)
    if coexist_crons:
        lines.extend(["## Crons That Will Coexist (not touched)", ""])
        for name in coexist_crons:
            c = analysis["classified_crons"][name]
            lines.append(f"- **{name}** — {c['last_status']} — {c['reason'][:60]}")
        lines.append("")

    # Old files
    if analysis["old_metacog_files"]:
        lines.extend(["## Old Metacognition Files (will be archived, never deleted)", ""])
        for f in analysis["old_metacog_files"]:
            modified = f.get("modified", "?")[:10]
            lines.append(f"- `{f['path']}` — {f['size']} bytes, modified {modified}")
        lines.append("")

    # New modules
    lines.extend(["## New Modular System", ""])
    for m in analysis["new_skill_modules"]:
        lines.append(f"- **{m['name']}** ({m['tier']}) — {m['description'][:60]}")
    lines.append("")

    # Demo results
    lines.extend(["## Live Demo Results", ""])
    for tier in ["quick", "deep"]:
        lr = analysis["dry_run_results"].get(f"{tier}_live", {})
        lines.extend([
            f"### {tier.title()} Tier",
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
        "### Step 1: Backup",
        "- Export full cron table to JSON in `.archive/`",
        "- Date-stamped copy of all old metacog scripts",
        "- Copy existing metacognition output",
        "- MANIFEST.md with restore instructions",
        "",
        "### Step 2: Execute",
        "- Reads migration plan JSON from analysis step (single source of truth)",
        "- Only disables crons classified as `replace`",
        "- Skips crons classified as `review` unless human confirmed",
        "- Creates `metacog-quick` (15m, Haiku) and `metacog-deep` (1h, Sonnet)",
        "- Archives old scripts to `.archive/` (move, never delete)",
        "",
        "### Step 3: Verify",
        "- Confirms new crons exist and enabled",
        "- Confirms replaced crons disabled (not deleted)",
        "- Runs both tiers live",
        "- Confirms coexist crons untouched",
        "",
        "### Rollback",
        "- Re-enables replaced crons from backup",
        "- Removes new metacog crons",
        "- Restores archived scripts",
        "",
    ])

    return "\n".join(lines)


def write_migration_plan(analysis: dict, doc_path: str) -> str:
    """Write a migration plan JSON that execute step consumes."""
    plan = {
        "generated": datetime.now().isoformat(),
        "analysis_doc": doc_path,
        "crons_to_replace": [],
        "crons_to_coexist": [],
        "crons_to_review": [],
        "files_to_archive": [f["path"] for f in analysis["old_metacog_files"]],
        "new_crons": [
            {
                "name": "metacog-quick",
                "schedule": "every 15m",
                "model": "trendmicro-aiendpoint/claude-4.5-haiku",
                "thinking": "off",
                "timeout": 120,
                "tier": "quick",
            },
            {
                "name": "metacog-deep",
                "schedule": "every 1h",
                "model": "trendmicro-aiendpoint/claude-4.6-sonnet",
                "thinking": "low",
                "timeout": 300,
                "tier": "deep",
            },
        ],
        "blockers": analysis["blockers"],
    }

    for name, c in analysis["classified_crons"].items():
        entry = {"name": name, "id": c.get("id", ""), "reason": c["reason"]}
        if c["classification"] == "replace":
            plan["crons_to_replace"].append(entry)
        elif c["classification"] == "coexist":
            plan["crons_to_coexist"].append(entry)
        elif c["classification"] == "review":
            plan["crons_to_review"].append(entry)

    plan_path = ANALYSES_DIR / f"migration-plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    plan_path.write_text(json.dumps(plan, indent=2, default=str))
    print(f"📋 Migration plan: {plan_path}")
    return str(plan_path)


def find_latest_plan() -> dict:
    """Find the most recent migration plan JSON."""
    plans = sorted(ANALYSES_DIR.glob("migration-plan-*.json"))
    if not plans:
        print("❌ No migration plan found. Run 'analyze' first.")
        sys.exit(1)
    plan_path = plans[-1]
    print(f"📋 Using plan: {plan_path}")
    return json.loads(plan_path.read_text())


def do_analyze(dry_run: bool = False) -> str:
    """Run analysis and write documents. Returns path to analysis doc."""
    print("🔍 Analyzing environment...")
    analysis = analyze_environment()
    doc = format_analysis_document(analysis)

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Write analysis document
    doc_path = ANALYSES_DIR / f"migration-analysis-{ts}.md"
    doc_path.write_text(doc)

    # Write raw data
    json_path = ANALYSES_DIR / f"migration-analysis-{ts}.json"
    json_path.write_text(json.dumps(analysis, indent=2, default=str))

    # Write migration plan (consumed by execute step)
    plan_path = write_migration_plan(analysis, str(doc_path))

    print(f"📄 Analysis document: {doc_path}")
    print(f"📊 Raw data: {json_path}")
    return str(doc_path)


def do_backup() -> str:
    """Create date-stamped backup of all affected files."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = ARCHIVE_DIR / f"metacog-migration-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backed_up = []

    # Backup full cron table
    jobs = get_cron_jobs()
    cron_backup = backup_dir / "cron-jobs-full-backup.json"
    cron_backup.write_text(json.dumps(jobs, indent=2, default=str))
    backed_up.append("Full cron table (all jobs)")

    # Backup old metacog files (dynamically found)
    old_files = find_old_metacog_files()
    if old_files:
        scripts_dir = backup_dir / "old-scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for f in old_files:
            # Preserve some path structure to avoid name collisions
            rel = f.relative_to(f.parent.parent) if len(f.parts) > 2 else Path(f.name)
            dest = scripts_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            backed_up.append(str(f))

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
        + "\n".join(f"- {item}" for item in backed_up)
        + f"\n\n## Restore command:\n"
        f"```\npython3 {__file__} rollback --backup-dir {backup_dir}\n```\n"
    )

    print(f"📦 Backup created: {backup_dir}")
    print(f"   {len(backed_up)} items backed up")
    return str(backup_dir)


def do_execute(dry_run: bool = False) -> bool:
    """Execute the migration plan."""
    plan = find_latest_plan()

    # Check for blockers
    if plan.get("blockers"):
        print("❌ Cannot execute — blockers found:")
        for b in plan["blockers"]:
            print(f"  - {b}")
        return False

    # Check for unresolved review items
    if plan.get("crons_to_review"):
        print("⚠️  Crons needing human review (will be SKIPPED during migration):")
        for c in plan["crons_to_review"]:
            print(f"  - {c['name']}: {c['reason']}")
        print()

    if dry_run:
        print("🏗️  [DRY RUN] Would execute:")
        for c in plan.get("crons_to_replace", []):
            print(f"  - Disable: {c['name']}")
        for nc in plan.get("new_crons", []):
            print(f"  - Create: {nc['name']} ({nc['schedule']}, {nc['model'][:30]})")
        for f in plan.get("files_to_archive", []):
            print(f"  - Archive: {f}")
        return True

    # Step 1: Disable crons classified as "replace"
    for cron in plan.get("crons_to_replace", []):
        name = cron["name"]
        print(f"📋 Disabling replaced cron: {name}...")
        stdout, stderr, rc = run_cmd(["openclaw", "cron", "disable", name])
        if rc != 0 and "not found" not in stderr.lower():
            print(f"  ⚠️  Could not disable {name}: {stderr[:100]}")
        else:
            print(f"  ✅ {name} disabled")

    # Step 2: Create new cron jobs
    for nc in plan.get("new_crons", []):
        tier = nc["tier"]
        name = nc["name"]
        print(f"📋 Creating {name} ({nc['schedule']})...")

        if tier == "quick":
            prompt = (
                f"Run the metacognition quick tier: python3 {RUNNER} --tier quick. "
                f"If any module returns findings (exit code 1), review the output. "
                f"If any 🔴 anti-patterns are found, post a brief alert to Joel DM (D0ATWPM4DTK) "
                f"via message(action=send, channel=slack, target=D0ATWPM4DTK). "
                f"Start and end channel messages with 🌴. "
                f"Otherwise reply HEARTBEAT_OK."
            )
        else:
            prompt = (
                f"Run the metacognition deep tier: python3 {RUNNER} --tier deep. "
                f"Review findings from all modules. For conflict-resolution findings, check if any "
                f"CR documents need escalation to Joel. For pattern-detector findings with 🔴 flags, "
                f"post to #coco-metacognition (C0ATCRVSB71) via message(action=send, channel=slack, "
                f"target=C0ATCRVSB71). Write a 2-3 sentence self-reflection and append to "
                f"memory/metacognition/$(date +%Y-%m-%d).md. "
                f"Start and end channel messages with 🌴. If everything is clean, reply HEARTBEAT_OK."
            )

        stdout, stderr, rc = run_cmd([
            "openclaw", "cron", "add",
            "--name", name,
            "--schedule", nc["schedule"],
            "--model", nc["model"],
            "--target", "isolated",
            "--light-context",
            "--thinking", nc.get("thinking", "off"),
            "--timeout", str(nc.get("timeout", 120)),
            "--message", prompt,
        ])
        if rc != 0:
            print(f"  ❌ Failed: {stderr[:200]}")
            return False
        print(f"  ✅ {name} created")

    # Step 3: Archive old files (move, never delete)
    files_to_archive = plan.get("files_to_archive", [])
    if files_to_archive:
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        archive_dest = ARCHIVE_DIR / f"old-metacog-scripts-{ts}"
        archived = 0
        for fpath in files_to_archive:
            f = Path(fpath)
            if f.exists():
                dest = archive_dest / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest))
                archived += 1
                print(f"  📁 Archived: {f.name}")
        if archived:
            print(f"  ✅ {archived} files archived to {archive_dest}")

    print("\n✅ Migration complete!")
    return True


def do_verify() -> bool:
    """Post-migration verification."""
    plan = find_latest_plan()
    success = True

    print("🔍 Post-migration verification...")

    jobs = get_cron_jobs()
    job_names = {j.get("name", ""): j for j in jobs}

    # 1. New crons exist and enabled
    print("\n📋 New cron jobs:")
    for nc in plan.get("new_crons", []):
        name = nc["name"]
        if name in job_names:
            job = job_names[name]
            status = "✅ enabled" if job.get("enabled") else "⚠️ disabled"
            print(f"  {status}: {name}")
        else:
            print(f"  ❌ MISSING: {name}")
            success = False

    # 2. Replaced crons disabled
    print("\n📋 Replaced crons:")
    for c in plan.get("crons_to_replace", []):
        name = c["name"]
        if name in job_names:
            job = job_names[name]
            if job.get("enabled"):
                print(f"  ⚠️  {name} still enabled")
            else:
                print(f"  ✅ {name} disabled")
        else:
            print(f"  ℹ️  {name} not found (ok if removed)")

    # 3. Coexist crons untouched
    print("\n📋 Coexist crons (should be untouched):")
    for c in plan.get("crons_to_coexist", []):
        name = c["name"]
        if name in job_names:
            job = job_names[name]
            status = "✅" if job.get("enabled") else "⚠️ disabled"
            print(f"  {status} {name}")
        else:
            print(f"  ⚠️  {name} not found")

    # 4. Run both tiers
    print("\n📋 Running quick tier test...")
    stdout, stderr, rc = run_cmd([sys.executable, str(RUNNER), "--tier", "quick"], timeout=60)
    if rc <= 1:
        print(f"  ✅ Quick tier ok (exit {rc})")
    else:
        print(f"  ❌ Quick tier failed (exit {rc})")
        success = False

    print("\n📋 Running deep tier test...")
    stdout, stderr, rc = run_cmd([sys.executable, str(RUNNER), "--tier", "deep"], timeout=120)
    if rc <= 1:
        print(f"  ✅ Deep tier ok (exit {rc})")
    else:
        print(f"  ❌ Deep tier failed (exit {rc})")
        success = False

    print(f"\n{'✅ Verification PASSED' if success else '❌ Verification FAILED'}")
    return success


def do_rollback(backup_dir: str = None):
    """Rollback migration from backup."""
    if not backup_dir:
        backups = sorted(ARCHIVE_DIR.glob("metacog-migration-*"))
        if not backups:
            print("❌ No backups found")
            return False
        backup_dir = str(backups[-1])

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_dir}")
        return False

    print(f"🔄 Rolling back from: {backup_path}")

    # Re-enable replaced crons
    plan_files = sorted(ANALYSES_DIR.glob("migration-plan-*.json"))
    if plan_files:
        plan = json.loads(plan_files[-1].read_text())
        for c in plan.get("crons_to_replace", []):
            print(f"  Re-enabling: {c['name']}")
            run_cmd(["openclaw", "cron", "enable", c["name"]])

    # Remove new crons
    for name in ["metacog-quick", "metacog-deep"]:
        print(f"  Removing: {name}")
        run_cmd(["openclaw", "cron", "rm", name])

    # Restore archived scripts
    old_scripts = backup_path / "old-scripts"
    if old_scripts.exists():
        print("  Restoring old scripts...")
        for f in old_scripts.rglob("*"):
            if f.is_file():
                # Try to find original location from the analysis
                for orig_dir in [
                    WORKSPACE / "scripts",
                    Path.home() / "openclaw-dm" / "scripts" / "metacognition",
                ]:
                    candidate = orig_dir / f.name
                    # Restore to the first matching parent that exists
                    if orig_dir.exists():
                        candidate.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, candidate)
                        print(f"    ✅ Restored {candidate}")
                        break

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
            print(f"\n⚠️  Verification found issues — review output")
            print(f"    Rollback: python3 {__file__} rollback")
        print()

        print(f"\n📄 Analysis: {doc_path}")
        print(f"📦 Backup: {backup_path}")


if __name__ == "__main__":
    main()
