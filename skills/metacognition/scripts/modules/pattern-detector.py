#!/usr/bin/env python3
"""Module: pattern-detector — Detect circular rebuilds and repeated failures.

Looks for signs that the agent is stuck in loops: building and tearing down
the same thing, retrying failed approaches, or spending excessive tokens on
the same topic across sessions.

Tier: deep (1-hour cron)
"""

import argparse
import collections
import glob
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
WORKSPACE = Path.home() / ".openclaw" / "workspace"


def scan_for_circular_topics(since_ts: float) -> list:
    """Find topics discussed in many sessions (possible circular rebuilds)."""
    # Track unique file paths written across sessions
    session_writes = collections.defaultdict(set)  # {file: set(session_ids)}

    for f in sorted(glob.glob(str(SESSIONS_DIR / "*.jsonl"))):
        if os.path.getmtime(f) < since_ts:
            continue
        session_id = Path(f).stem
        try:
            with open(f) as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        content = d.get("message", {}).get("content", [])
                        if not isinstance(content, list):
                            continue
                        for c in content:
                            if not isinstance(c, dict):
                                continue
                            if c.get("type") == "toolCall" and c.get("name") == "write":
                                path = c.get("arguments", {}).get("path", "")
                                if path and "/tmp/" not in path:
                                    session_writes[path].add(session_id)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    # Files written in many different sessions = possible circular rebuild
    circular = []
    for path, sessions in session_writes.items():
        if len(sessions) >= 5:
            circular.append(f"🔴 Circular: {path} written in {len(sessions)} different sessions")

    return circular


def scan_for_repeated_errors(since_ts: float) -> list:
    """Find error patterns that repeat across sessions."""
    error_patterns = collections.Counter()

    for f in sorted(glob.glob(str(SESSIONS_DIR / "*.jsonl"))):
        if os.path.getmtime(f) < since_ts:
            continue
        try:
            with open(f) as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        content = d.get("message", {}).get("content", [])
                        if isinstance(content, str) and "error" in content.lower():
                            # Extract first 80 chars of error-containing text
                            idx = content.lower().index("error")
                            snippet = content[max(0, idx - 20):idx + 60].strip()
                            error_patterns[snippet[:80]] += 1
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    text = c.get("text", "")
                                    if "error" in text.lower() and len(text) < 500:
                                        error_patterns[text[:80]] += 1
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    findings = []
    for pattern, count in error_patterns.most_common(5):
        if count >= 10:
            findings.append(f"🟡 Repeated error ({count}x): {pattern[:60]}...")

    return findings


def run(output_dir: Path) -> int:
    days = int(os.environ.get("METACOG_DAYS", "3"))
    since = datetime.now() - timedelta(days=days)

    findings = []
    findings.extend(scan_for_circular_topics(since.timestamp()))
    findings.extend(scan_for_repeated_errors(since.timestamp()))

    if findings:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — Pattern Detector\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        print(f"📋 {len(findings)} pattern(s) detected:")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("✅ No circular patterns or repeated errors detected")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    parser.add_argument("--days", type=int, default=3)
    args = parser.parse_args()
    if args.days:
        os.environ["METACOG_DAYS"] = str(args.days)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
