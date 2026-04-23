#!/usr/bin/env python3
"""Metacognition session analyzer.

Analyzes session transcripts to find:
- Repeated patterns (same commands run hundreds of times)
- Decision loss (topics discussed then forgotten)
- Circular rebuilds (building/tearing down the same thing)
- Token waste (empty polls, redundant reads)

Usage:
    python3 analyze_sessions.py                  # Today's sessions
    python3 analyze_sessions.py --days 3         # Last 3 days
    python3 analyze_sessions.py --output report  # Write to file
"""

import json
import os
import glob
import collections
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "memory" / "metacognition"


def analyze_sessions(since_ts: float):
    """Analyze all sessions modified since timestamp."""
    tool_counts = collections.Counter()
    exec_cmds = collections.Counter()
    read_files = collections.Counter()
    write_files = collections.Counter()
    edit_files = collections.Counter()
    message_targets = collections.Counter()
    total_sessions = 0
    compactions = 0
    errors = []
    topics_mentioned = collections.Counter()

    # Keywords that indicate architectural decisions or topic shifts
    decision_keywords = [
        "webhook", "native", "polling", "architecture", "decision",
        "migrate", "replace", "refactor", "redesign", "instead of",
        "should we", "let's use", "don't use", "stop using",
        "root cause", "the real problem"
    ]

    for f in sorted(glob.glob(str(SESSIONS_DIR / "*.jsonl"))):
        if os.path.getmtime(f) < since_ts:
            continue
        total_sessions += 1

        try:
            with open(f) as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        if d.get("type") == "compaction":
                            compactions += 1

                        msg = d.get("message", {})
                        role = msg.get("role", "")
                        content = msg.get("content", [])

                        if not isinstance(content, list):
                            # Check for decision keywords in text content
                            if isinstance(content, str):
                                for kw in decision_keywords:
                                    if kw.lower() in content.lower():
                                        topics_mentioned[kw] += 1
                            continue

                        for c in content:
                            if not isinstance(c, dict):
                                continue

                            # Tool calls
                            if c.get("type") == "toolCall":
                                name = c.get("name", "?")
                                tool_counts[name] += 1
                                args = c.get("arguments", {})

                                if name == "exec":
                                    cmd = args.get("command", "")[:100]
                                    exec_cmds[cmd] += 1
                                elif name == "read":
                                    read_files[args.get("path", "?")] += 1
                                elif name == "write":
                                    write_files[args.get("path", "?")] += 1
                                elif name == "edit":
                                    edit_files[args.get("path", "?")] += 1
                                elif name == "message":
                                    target = args.get("target", "?")
                                    message_targets[target] += 1

                            # Check text content for decision keywords
                            if c.get("type") == "text":
                                text = c.get("text", "")
                                for kw in decision_keywords:
                                    if kw.lower() in text.lower():
                                        topics_mentioned[kw] += 1

                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            errors.append(f"{f}: {e}")

    return {
        "total_sessions": total_sessions,
        "compactions": compactions,
        "tool_counts": tool_counts,
        "exec_cmds": exec_cmds,
        "read_files": read_files,
        "write_files": write_files,
        "edit_files": edit_files,
        "message_targets": message_targets,
        "topics_mentioned": topics_mentioned,
        "errors": errors[:10],
    }


def format_report(data: dict, days: int) -> str:
    """Format analysis into readable report."""
    lines = [
        f"# Metacognition Session Analysis",
        f"Period: last {days} day(s) | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M CDT')}",
        "",
        f"## Summary",
        f"- Sessions: {data['total_sessions']}",
        f"- Compactions (context resets): {data['compactions']}",
        f"- Avg compactions/session: {data['compactions']/max(data['total_sessions'],1):.1f}",
        "",
        f"## Tool Usage (top 10)",
    ]
    for tool, count in data["tool_counts"].most_common(10):
        lines.append(f"- {tool}: {count:,}")

    lines.extend(["", "## Most Repeated Commands (RED FLAGS)"])
    for cmd, count in data["exec_cmds"].most_common(10):
        flag = " ⚠️ EXCESSIVE" if count > 100 else ""
        lines.append(f"- [{count:,}x]{flag} `{cmd[:80]}`")

    lines.extend(["", "## Most Read Files (what am I re-reading?)"])
    for f, count in data["read_files"].most_common(10):
        lines.append(f"- [{count}x] {f}")

    lines.extend(["", "## Most Written Files (what am I re-writing?)"])
    for f, count in data["write_files"].most_common(10):
        lines.append(f"- [{count}x] {f}")

    lines.extend(["", "## Decision Keywords Frequency"])
    for kw, count in data["topics_mentioned"].most_common(15):
        lines.append(f"- \"{kw}\": {count}")

    lines.extend(["", "## Anti-Patterns Detected"])

    # Detect patterns
    top_cmd = data["exec_cmds"].most_common(1)
    if top_cmd and top_cmd[0][1] > 500:
        lines.append(f"- 🔴 **Token hemorrhage**: `{top_cmd[0][0][:60]}` called {top_cmd[0][1]:,} times")

    if data["compactions"] > 50:
        lines.append(f"- 🔴 **Amnesia cycle**: {data['compactions']} compactions = {data['compactions']} context resets")

    poll_count = sum(c for cmd, c in data["exec_cmds"].items() if "poll_all" in cmd)
    if poll_count > 1000:
        lines.append(f"- 🔴 **Polling addiction**: poll_all.py called {poll_count:,} times")

    # Check for circular patterns (same file written many times)
    for f, count in data["write_files"].most_common(5):
        if count > 20 and "/tmp/" not in f:
            lines.append(f"- 🟡 **Circular edits**: {f} written {count} times")

    lines.extend(["", "## Recommendations"])
    if poll_count > 1000:
        lines.append("- Replace polling with native OpenClaw msteams channel")
    if data["compactions"] > 50:
        lines.append("- Enable Dreaming for automatic memory consolidation")
        lines.append("- Write DECISIONS.md and inject into bootstrap context")
    lines.append("- Review this report every metacognition cycle")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Metacognition session analyzer")
    parser.add_argument("--days", type=int, default=1, help="Days to analyze")
    parser.add_argument("--output", choices=["stdout", "report"], default="stdout")
    args = parser.parse_args()

    since = datetime.now() - timedelta(days=args.days)
    since_ts = since.timestamp()

    data = analyze_sessions(since_ts)
    report = format_report(data, args.days)

    if args.output == "report":
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        outfile = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}-analysis.md"
        outfile.write_text(report)
        print(f"Report written to {outfile}")
    else:
        print(report)


if __name__ == "__main__":
    main()
