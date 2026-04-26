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
import re
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


# Skip these noisy patterns — common in tool output, not real errors
ERROR_SKIP_PATTERNS = [
    r'^\{',                     # JSON fragments
    r'^\[',                     # JSON arrays
    r'usage:',                  # CLI usage messages (argparse)
    r'unrecognized arguments',  # argparse noise
    r'Expected \d+ argument',   # tool validation noise
    r'error:.*too many arguments for', # OpenClaw tool validation
    r'HEARTBEAT_OK',
    r'^\s*$',                   # blank
]


def _is_noise(snippet: str) -> bool:
    """Return True if snippet matches known noise patterns."""
    for pat in ERROR_SKIP_PATTERNS:
        if re.search(pat, snippet, re.IGNORECASE):
            return True
    # Too short to be meaningful
    if len(snippet.strip()) < 10:
        return True
    return False


def scan_for_repeated_errors(since_ts: float) -> list:
    """Find error patterns that repeat across sessions.

    Only counts errors from tool results (role=tool), not from agent text
    or user messages — those are too noisy.
    """
    error_patterns = collections.Counter()

    for f in sorted(glob.glob(str(SESSIONS_DIR / "*.jsonl"))):
        if os.path.getmtime(f) < since_ts:
            continue
        try:
            with open(f) as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        msg = d.get("message", {})
                        role = msg.get("role", "")
                        # Only look at tool results — agent text is too noisy
                        if role != "tool":
                            continue
                        content = msg.get("content", [])
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            text = " ".join(
                                c.get("text", "") for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            )
                        else:
                            continue
                        # Only match lines that start with "error" or contain
                        # common error prefixes (not just any mention of the word)
                        for err_line in text.splitlines():
                            err_line = err_line.strip()
                            if not err_line:
                                continue
                            lower = err_line.lower()
                            is_error = (
                                lower.startswith("error") or
                                lower.startswith("traceback") or
                                ": error:" in lower or
                                "exception:" in lower or
                                "failed:" in lower or
                                "command exited with code" in lower
                            )
                            if is_error:
                                snippet = err_line[:80]
                                if not _is_noise(snippet):
                                    error_patterns[snippet] += 1
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
