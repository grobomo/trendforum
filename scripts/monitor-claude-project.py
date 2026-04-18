#!/usr/bin/env python3
"""Monitor a Claude Code project for progress and report via Teams.

Checks git history, todo lists, notes, and code changes every 15 minutes.
Posts summary to Teams private chat.
"""
import subprocess
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_PATH = "/mnt/c/Users/joelg/Documents/ProjectsCL1/_tmemu/openclaw"
STATE_FILE = Path.home() / ".openclaw" / "teams-poller" / "monitor-state.json"
REPLY_SCRIPT = str(Path(__file__).parent / "teams-poller" / "queue_reply.py")


def run(cmd, cwd=None, timeout=30):
    """Run a command and return stdout."""
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"(error: {e})"


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main():
    if not os.path.isdir(PROJECT_PATH):
        print(f"Project path not found: {PROJECT_PATH}", file=sys.stderr)
        return

    state = load_state()
    last_check = state.get("last_check", "")
    last_commit = state.get("last_commit", "")

    # Git log since last check (or last 15 min)
    since = last_check or (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    git_log = run(f'git log --oneline --since="{since}" --all 2>/dev/null', cwd=PROJECT_PATH)
    
    # Current branch + status
    branch = run("git branch --show-current 2>/dev/null", cwd=PROJECT_PATH)
    status = run("git status --short 2>/dev/null", cwd=PROJECT_PATH)
    
    # Latest commit
    latest = run("git log -1 --format='%h %s (%ar)' 2>/dev/null", cwd=PROJECT_PATH)
    
    # Diff stats since last check
    diff_stat = ""
    if last_commit:
        diff_stat = run(f"git diff --stat {last_commit}..HEAD 2>/dev/null", cwd=PROJECT_PATH)
    
    # Check for TODO files
    todos = ""
    for pattern in ["TODO*", "todo*", "TASKS*", "tasks*"]:
        found = run(f"find . -maxdepth 2 -name '{pattern}' -type f 2>/dev/null", cwd=PROJECT_PATH)
        if found:
            for f in found.split('\n')[:3]:
                content = run(f"head -20 '{f}' 2>/dev/null", cwd=PROJECT_PATH)
                if content:
                    todos += f"\n**{f}:**\n{content[:300]}\n"

    # Count files changed
    current_commit = run("git rev-parse --short HEAD 2>/dev/null", cwd=PROJECT_PATH)

    # Build report
    has_activity = bool(git_log) or bool(status)
    
    if not has_activity:
        # No changes since last check — skip report
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return

    parts = ["🌴 **Claude Code Project Monitor** — `_tmemu/openclaw`\n"]
    
    if branch:
        parts.append(f"**Branch:** `{branch}`")
    
    if git_log:
        parts.append(f"\n**New commits since last check:**\n```\n{git_log[:500]}\n```")
    
    if diff_stat:
        parts.append(f"\n**Changes:**\n```\n{diff_stat[:400]}\n```")
    
    if status:
        parts.append(f"\n**Uncommitted changes:**\n```\n{status[:300]}\n```")
    
    if latest:
        parts.append(f"\n**Latest commit:** `{latest}`")
    
    if todos:
        parts.append(f"\n**TODO files:**{todos[:500]}")
    
    parts.append("\n🌴")
    
    report = "\n".join(parts)
    
    # Queue the report via the reply script (to private chat)
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(report)
        tmpfile = f.name
    
    subprocess.run(f"python3 {REPLY_SCRIPT} < {tmpfile}", shell=True, timeout=10)
    os.unlink(tmpfile)
    
    # Update state
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    if current_commit:
        state["last_commit"] = current_commit
    save_state(state)
    
    print(f"Report sent ({len(report)} chars)")


if __name__ == "__main__":
    main()
