#!/usr/bin/env python3
"""Module: conflict-resolution — Detect knowledge conflicts.

Scans lesson files for contradictions with each other and flags conflicts
that need CR documents. This is the automated detector; the actual resolution
process is guided by the agent following the skill's resolution process.

Tier: deep (1-hour cron)
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"


def load_lessons(lessons_dir: Path) -> dict:
    """Load all lesson files, return {filename: content}."""
    lessons = {}
    if not lessons_dir.exists():
        return lessons
    for f in sorted(lessons_dir.glob("*.md")):
        if f.name == "TEMPLATE.md":
            continue
        try:
            lessons[f.name] = f.read_text()
        except Exception:
            pass
    return lessons


def load_cr_docs(cr_dir: Path) -> dict:
    """Load existing conflict resolution documents."""
    docs = {}
    if not cr_dir.exists():
        return docs
    for f in sorted(cr_dir.glob("CR-*.md")):
        try:
            docs[f.name] = f.read_text()
        except Exception:
            pass
    return docs


def extract_hook_references(content: str) -> list:
    """Extract hook types referenced in a lesson."""
    hook_types = [
        "before_tool_call", "after_tool_call", "before_agent_reply",
        "session_start", "llm_input", "llm_output", "message_sending",
    ]
    found = []
    for ht in hook_types:
        if ht in content:
            found.append(ht)
    return found


def extract_claims(content: str) -> list:
    """Extract key claims from a lesson (simple heuristic)."""
    claims = []
    # Look for "MUST", "NEVER", "ALWAYS", "can't", "cannot"
    for line in content.splitlines():
        line = line.strip()
        if re.search(r'\b(MUST|NEVER|ALWAYS|cannot|can\'t|do not|don\'t)\b', line, re.IGNORECASE):
            if len(line) > 20 and len(line) < 300:
                claims.append(line)
    return claims


def check_hook_conflicts(lessons: dict) -> list:
    """Check for conflicting hook architecture claims across lessons."""
    conflicts = []

    # Gather all hook-related claims
    hook_claims = {}
    for name, content in lessons.items():
        refs = extract_hook_references(content)
        if refs:
            hook_claims[name] = {
                "hooks": refs,
                "claims": extract_claims(content),
                "content": content,
            }

    # Cross-check: if lesson A says "X can't do Y" and lesson B assumes "X does Y"
    for name_a, data_a in hook_claims.items():
        for name_b, data_b in hook_claims.items():
            if name_a >= name_b:
                continue
            # Check if they reference the same hooks with contradictory claims
            shared_hooks = set(data_a["hooks"]) & set(data_b["hooks"])
            if shared_hooks:
                # Look for "can't" vs "can" patterns about the same hook
                for hook in shared_hooks:
                    a_negative = any(
                        f"can't" in c.lower() or "cannot" in c.lower()
                        for c in data_a["claims"] if hook in c
                    )
                    b_positive = any(
                        "can " in c.lower() and "can't" not in c.lower()
                        for c in data_b["claims"] if hook in c
                    )
                    if a_negative and b_positive:
                        conflicts.append(
                            f"Potential conflict: {name_a} says {hook} can't do something, "
                            f"but {name_b} assumes it can"
                        )

    return conflicts


def check_unresolved(cr_docs: dict) -> list:
    """Check for CR docs still in draft or pending-review."""
    unresolved = []
    for name, content in cr_docs.items():
        if "`draft`" in content or "`pending-review`" in content:
            # Extract title
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else name
            unresolved.append(f"Unresolved CR: {title} ({name})")
    return unresolved


def run(output_dir: Path) -> int:
    lessons_dir = WORKSPACE / os.environ.get("METACOG_LESSONS_DIRECTORY", "memory/lessons")
    cr_dir = WORKSPACE / os.environ.get("METACOG_CR_DIRECTORY", "memory/conflict-resolutions")

    lessons = load_lessons(lessons_dir)
    cr_docs = load_cr_docs(cr_dir)
    findings = []

    # Check for hook architecture conflicts
    hook_conflicts = check_hook_conflicts(lessons)
    findings.extend(hook_conflicts)

    # Check for unresolved CRs
    unresolved = check_unresolved(cr_docs)
    findings.extend(unresolved)

    # Stats
    print(f"Scanned {len(lessons)} lessons, {len(cr_docs)} CR docs")

    if findings:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — Conflict Resolution\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        print(f"📋 {len(findings)} finding(s):")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("✅ No conflicts detected")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
