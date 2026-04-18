#!/usr/bin/env python3
"""Monitor Claude Code project and post narrative summaries to Slack DM.

Every 15 min, checks git activity in the monitored project.
Only posts when there's actual new activity. Writes human-readable
summaries, not raw terminal dumps.
"""
import subprocess
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_PATH = "/mnt/c/Users/joelg/Documents/ProjectsCL1/_tmemu/openclaw"
STATE_FILE = Path.home() / ".openclaw" / "teams-poller" / "monitor-state.json"

# Slack delivery via OpenClaw message tool isn't available from scripts.
# Instead, write summary to a file that poll_all.py can pick up,
# or post directly via Slack webhook/API.
SLACK_SUMMARY_FILE = "/tmp/claude-monitor-summary.txt"


def run(cmd, cwd=None, timeout=30):
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
    last_commit = state.get("last_commit", "")
    last_report_time = state.get("last_report_time", "")

    # Get current HEAD
    current_commit = run("git rev-parse --short HEAD 2>/dev/null", cwd=PROJECT_PATH)
    branch = run("git branch --show-current 2>/dev/null", cwd=PROJECT_PATH)
    
    # Check for uncommitted changes
    status = run("git status --short 2>/dev/null", cwd=PROJECT_PATH)
    uncommitted_count = len([l for l in status.split('\n') if l.strip()]) if status else 0

    # No new commits AND no change in uncommitted files? Skip.
    if current_commit == last_commit and uncommitted_count == state.get("last_uncommitted", 0):
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return  # Silent — no activity

    # New commits since last check
    new_commits = []
    if last_commit and last_commit != current_commit:
        log = run(f"git log --oneline {last_commit}..HEAD 2>/dev/null", cwd=PROJECT_PATH)
        if log:
            new_commits = [l.strip() for l in log.split('\n') if l.strip()]
    elif not last_commit:
        # First run — get last 3 commits for context
        log = run("git log --oneline -3 2>/dev/null", cwd=PROJECT_PATH)
        if log:
            new_commits = [l.strip() for l in log.split('\n') if l.strip()]

    # Diff stats (only if new commits)
    diff_summary = ""
    if last_commit and last_commit != current_commit:
        diff_stat = run(f"git diff --shortstat {last_commit}..HEAD 2>/dev/null", cwd=PROJECT_PATH)
        if diff_stat:
            diff_summary = diff_stat.strip()

    # Build narrative summary
    parts = ["🌴 *Claude Code Project Update* — `_tmemu/openclaw`\n"]

    if new_commits:
        commit_count = len(new_commits)
        parts.append(f"*{commit_count} new commit{'s' if commit_count > 1 else ''}* on `{branch}`:")
        # Show up to 5 commits, summarize if more
        for c in new_commits[:5]:
            parts.append(f"  • `{c}`")
        if len(new_commits) > 5:
            parts.append(f"  _...and {len(new_commits) - 5} more_")
    
    if diff_summary:
        parts.append(f"\n*Changes:* {diff_summary}")

    if uncommitted_count > 0:
        parts.append(f"\n*{uncommitted_count} uncommitted file{'s' if uncommitted_count > 1 else ''}* in working tree")

    if not new_commits and uncommitted_count > 0:
        parts.append(f"Branch `{branch}` — no new commits, but working tree changed")

    parts.append("\n🌴")
    
    summary = "\n".join(parts)

    # Write summary for Slack delivery
    Path(SLACK_SUMMARY_FILE).write_text(summary)
    print(summary)

    # Update state
    state["last_commit"] = current_commit
    state["last_uncommitted"] = uncommitted_count
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    state["last_report_time"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
