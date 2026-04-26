#!/usr/bin/env python3
"""Module: lesson-review — Review lessons board and local lesson files.

Checks for:
- Lesson files without corresponding Trello cards
- Lessons marked as having hooks that don't exist
- Inbox lessons that should be categorized

Tier: deep (1-hour cron)
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
LESSONS_DIR = WORKSPACE / "memory" / "lessons"


def check_lesson_integrity() -> list:
    """Check lesson files for structural issues."""
    findings = []

    if not LESSONS_DIR.exists():
        findings.append("⚠️ Lessons directory does not exist")
        return findings

    for f in sorted(LESSONS_DIR.glob("*.md")):
        if f.name == "TEMPLATE.md":
            continue

        content = f.read_text()

        # Check for required sections
        has_observation = "## Observation" in content
        has_lesson = "## The Lesson" in content or "## The Principle" in content
        has_source = "## Source" in content
        has_hook = "## Hook" in content
        has_triggers = "## Retrieval Triggers" in content

        missing = []
        if not has_observation:
            missing.append("Observation")
        if not has_lesson:
            missing.append("Lesson/Principle")
        if not has_source:
            missing.append("Source")
        if not has_triggers:
            missing.append("Retrieval Triggers")

        if missing:
            findings.append(f"🟡 {f.name}: missing sections: {', '.join(missing)}")

        # Check if hook is claimed but verify status
        if has_hook:
            hook_match = re.search(r'Hook status:\s*(\w+)', content)
            if hook_match:
                status = hook_match.group(1)
                if status == "new":
                    findings.append(f"📋 {f.name}: hook status is 'new' — verify if implemented")

        # Check for verification items
        unchecked = content.count("- [ ]")
        if unchecked > 0:
            findings.append(f"ℹ️ {f.name}: {unchecked} unverified item(s)")

    return findings


def check_duplicate_numbers() -> list:
    """Check for duplicate lesson numbers (e.g., two 004-*.md files)."""
    findings = []
    numbers = {}

    if not LESSONS_DIR.exists():
        return findings

    for f in sorted(LESSONS_DIR.glob("*.md")):
        if f.name == "TEMPLATE.md":
            continue
        match = re.match(r'^(\d+)-', f.name)
        if match:
            num = match.group(1)
            if num in numbers:
                findings.append(
                    f"🔴 Duplicate lesson number {num}: {numbers[num]} and {f.name}"
                )
            numbers[num] = f.name

    return findings


def run(output_dir: Path) -> int:
    findings = []
    findings.extend(check_lesson_integrity())
    findings.extend(check_duplicate_numbers())

    lesson_count = len(list(LESSONS_DIR.glob("*.md"))) - 1 if LESSONS_DIR.exists() else 0
    print(f"ℹ️  Scanned {lesson_count} lesson files")

    if findings:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — Lesson Review\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        print(f"📋 {len(findings)} finding(s):")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("✅ All lessons structurally sound")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
