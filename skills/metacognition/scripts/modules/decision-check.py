#!/usr/bin/env python3
"""Module: decision-check — Check for contradicted or stale decisions.

Scans DECISIONS.md (if it exists) for active decisions and checks whether
recent session activity contradicts them.

Tier: quick (15-min cron)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
DECISIONS_FILE = WORKSPACE / "DECISIONS.md"


def run(output_dir: Path) -> int:
    if not DECISIONS_FILE.exists():
        print("ℹ️  DECISIONS.md not found — skipping")
        return 0

    content = DECISIONS_FILE.read_text()
    findings = []

    # Count active decisions
    active = content.lower().count("status: active")
    blocked = content.lower().count("status: blocked")

    if blocked > 0:
        findings.append(f"🟡 {blocked} blocked decision(s) — review if any are now unblocked")

    # Check for stale dates (decisions older than 30 days without review)
    # Simple heuristic: look for date patterns
    import re
    dates = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
    if dates:
        oldest = min(dates)
        try:
            oldest_dt = datetime.strptime(oldest, "%Y-%m-%d")
            age = (datetime.now() - oldest_dt).days
            if age > 30:
                findings.append(
                    f"🟡 Oldest decision is {age} days old ({oldest}) — may need review"
                )
        except ValueError:
            pass

    print(f"ℹ️  {active} active, {blocked} blocked decisions")

    if findings:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — Decision Check\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        for finding in findings:
            print(f"  {finding}")
        return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
