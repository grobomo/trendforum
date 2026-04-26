#!/usr/bin/env python3
"""Module: session-analyzer — Quantitative session analysis.

Analyzes recent session transcripts for tool counts, command frequency,
anti-patterns (token hemorrhage, circular edits, polling addiction).

Tier: quick (15-min cron)
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

DECISION_KEYWORDS = [
    "webhook", "native", "polling", "architecture", "decision",
    "migrate", "replace", "refactor", "redesign", "instead of",
    "should we", "let's use", "don't use", "stop using",
    "root cause", "the real problem",
]


def analyze_sessions(since_ts: float) -> dict:
    """Analyze all sessions modified since timestamp."""
    tool_counts = collections.Counter()
    exec_cmds = collections.Counter()
    read_files = collections.Counter()
    write_files = collections.Counter()
    message_targets = collections.Counter()
    total_sessions = 0
    compactions = 0
    topics = collections.Counter()

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
                        content = msg.get("content", [])
                        if isinstance(content, str):
                            for kw in DECISION_KEYWORDS:
                                if kw.lower() in content.lower():
                                    topics[kw] += 1
                            continue
                        if not isinstance(content, list):
                            continue
                        for c in content:
                            if not isinstance(c, dict):
                                continue
                            if c.get("type") == "toolCall":
                                name = c.get("name", "?")
                                tool_counts[name] += 1
                                args = c.get("arguments", {})
                                if name == "exec":
                                    exec_cmds[args.get("command", "")[:100]] += 1
                                elif name == "read":
                                    read_files[args.get("path", "?")] += 1
                                elif name == "write":
                                    write_files[args.get("path", "?")] += 1
                                elif name == "message":
                                    message_targets[args.get("target", "?")] += 1
                            if c.get("type") == "text":
                                for kw in DECISION_KEYWORDS:
                                    if kw.lower() in c.get("text", "").lower():
                                        topics[kw] += 1
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    return {
        "total_sessions": total_sessions,
        "compactions": compactions,
        "tool_counts": tool_counts,
        "exec_cmds": exec_cmds,
        "read_files": read_files,
        "write_files": write_files,
        "message_targets": message_targets,
        "topics": topics,
    }


def run(output_dir: Path) -> int:
    days = int(os.environ.get("METACOG_DAYS", "1"))
    since = datetime.now() - timedelta(days=days)
    data = analyze_sessions(since.timestamp())

    findings = []

    # Anti-pattern: excessive command repetition
    for cmd, count in data["exec_cmds"].most_common(3):
        if count > 100:
            findings.append(f"🔴 Token hemorrhage: `{cmd[:60]}` called {count:,}x")

    # Anti-pattern: circular edits
    for f, count in data["write_files"].most_common(5):
        if count > 20 and "/tmp/" not in f:
            findings.append(f"🟡 Circular edits: {f} written {count}x")

    # Anti-pattern: excessive compactions
    if data["compactions"] > 50:
        findings.append(f"🔴 Amnesia cycle: {data['compactions']} compactions")

    # Stats line
    top_tools = ", ".join(f"{t}={c}" for t, c in data["tool_counts"].most_common(5))
    stats = f"Sessions: {data['total_sessions']} | Compactions: {data['compactions']} | Top tools: {top_tools}"

    if findings:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — Session Analyzer\n")
            f.write(f"- {stats}\n")
            for finding in findings:
                f.write(f"- {finding}\n")
        print(f"⚠️  {len(findings)} anti-pattern(s) detected")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print(f"✅ {stats}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()
    if args.days:
        os.environ["METACOG_DAYS"] = str(args.days)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
