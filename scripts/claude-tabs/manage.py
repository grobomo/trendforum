#!/usr/bin/env python3
"""Claude Code tab manager for Coconut.

Track, monitor, and manage Claude Code sessions launched via new_session.py.
Creates Trello cards for visibility, monitors progress, verifies completion.

Usage:
    # Launch a new Claude Code tab (creates tracker entry + Trello card)
    python3 manage.py launch --project /home/ubu/openclaw-dm --task "Build comms preprocessor" --task-id T001

    # Check status of all active tabs
    python3 manage.py status

    # Check a specific tab
    python3 manage.py status --tab-id <id>

    # Monitor all active tabs (check transcript activity, detect stalls)
    python3 manage.py monitor

    # Verify work is complete for a tab
    python3 manage.py verify --tab-id <id>

    # Close a tab (mark complete, update Trello card)
    python3 manage.py close --tab-id <id> --summary "Built classify.py, preprocessor, gate module"

    # List all tabs (active + completed)
    python3 manage.py list
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKER_FILE = os.path.join(SCRIPT_DIR, "tracker.json")
NEW_SESSION_PY = "/mnt/c/Users/joelg/Documents/ProjectsCL1/_grobomo/context-reset/new_session.py"

# Trello
TRELLO_LIST_ID = "69ebe51d36d2269f7c93de8c"  # Claude Code Tabs list


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_tracker():
    try:
        with open(TRACKER_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tabs": [], "trello_list_id": TRELLO_LIST_ID,
                "trello_board_id": "6954d3af836b51597afff8f2"}


def _save_tracker(data):
    os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _trello_creds():
    """Get Trello API key and token from keyring."""
    import keyring
    key = keyring.get_password("openclaw", "TRELLO_API_KEY")
    token = keyring.get_password("openclaw", "TRELLO_TOKEN")
    return key, token


def _trello_create_card(name, desc=""):
    """Create a Trello card in the Claude Code Tabs list."""
    import urllib.request
    import urllib.parse
    key, token = _trello_creds()
    if not key or not token:
        print("WARNING: Trello creds not found, skipping card creation", file=sys.stderr)
        return None

    params = urllib.parse.urlencode({
        "key": key, "token": token,
        "idList": TRELLO_LIST_ID,
        "name": name,
        "desc": desc,
        "pos": "bottom"
    })
    url = f"https://api.trello.com/1/cards?{params}"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            card = json.loads(resp.read())
            return card["id"]
    except Exception as e:
        print(f"WARNING: Trello card creation failed: {e}", file=sys.stderr)
        return None


def _trello_update_card(card_id, **kwargs):
    """Update a Trello card (name, desc, dueComplete, closed)."""
    import urllib.request
    import urllib.parse
    key, token = _trello_creds()
    if not key or not token:
        return

    params = urllib.parse.urlencode({"key": key, "token": token, **kwargs})
    url = f"https://api.trello.com/1/cards/{card_id}?{params}"
    req = urllib.request.Request(url, method="PUT", data=b"")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"WARNING: Trello update failed: {e}", file=sys.stderr)


def _trello_comment(card_id, text):
    """Add a comment to a Trello card."""
    import urllib.request
    import urllib.parse
    key, token = _trello_creds()
    if not key or not token:
        return

    params = urllib.parse.urlencode({"key": key, "token": token, "text": text})
    url = f"https://api.trello.com/1/cards/{card_id}/actions/comments?{params}"
    req = urllib.request.Request(url, method="POST", data=b"")
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"WARNING: Trello comment failed: {e}", file=sys.stderr)


def _find_pid(project_dir):
    """Find Claude Code PID for a project directory."""
    try:
        result = subprocess.run(
            ["pgrep", "-af", "claude"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            # Skip non-claude lines
            if "watchdog" in line or "pgrep" in line or "grep" in line:
                continue
            # Check if this process relates to our project
            if project_dir and os.path.basename(project_dir) in line:
                pid = line.split()[0]
                return int(pid)
    except Exception:
        pass
    return None


def _get_latest_jsonl(project_dir):
    """Get the most recent JSONL transcript for a project."""
    # Claude Code stores transcripts in ~/.claude/projects/<slug>/
    slug = project_dir.replace("/", "-").replace("\\", "-").replace(":", "-")
    # Try common slug patterns
    projects_dir = os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(projects_dir):
        return None, 0

    # Find matching project dir
    for d in os.listdir(projects_dir):
        # Slug encodes path: /home/ubu/openclaw-dm -> -home-ubu-openclaw-dm
        decoded = d.replace("-", "/")
        if project_dir.rstrip("/") in decoded or os.path.basename(project_dir) in d:
            proj_path = os.path.join(projects_dir, d)
            jsonls = [f for f in os.listdir(proj_path) if f.endswith(".jsonl")]
            if not jsonls:
                continue
            newest = max(jsonls, key=lambda f: os.path.getmtime(os.path.join(proj_path, f)))
            full = os.path.join(proj_path, newest)
            return full, os.path.getmtime(full)
    return None, 0


def _transcript_line_count(jsonl_path):
    """Count lines in a JSONL transcript."""
    try:
        with open(jsonl_path) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def cmd_launch(args):
    """Launch a new Claude Code tab and track it."""
    tracker = _load_tracker()

    # Generate tab ID
    tab_id = f"tab-{int(time.time())}"

    # Create Trello card
    card_name = f"🖥️ [{os.path.basename(args.project)}] {args.task}"
    card_desc = (
        f"**Project:** `{args.project}`\n"
        f"**Task:** {args.task}\n"
        f"**Task ID:** {args.task_id or 'N/A'}\n"
        f"**Launched:** {datetime.now().strftime('%Y-%m-%d %H:%M CDT')}\n"
        f"**Status:** 🟢 Active\n\n"
        f"---\n"
        f"Managed by Coconut via `scripts/claude-tabs/manage.py`"
    )
    card_id = _trello_create_card(card_name, card_desc)

    # Launch via new_session.py
    prompt = args.prompt or args.task
    cmd = [
        "python3", NEW_SESSION_PY,
        "--project-dir", args.project,
        "--prompt", prompt,
        "--no-close"
    ]

    print(f"Launching Claude Code for: {args.project}")
    print(f"Task: {args.task}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Find PID
    time.sleep(3)
    pid = _find_pid(args.project)

    # Record in tracker
    tab = {
        "id": tab_id,
        "project": args.project,
        "project_name": os.path.basename(args.project),
        "task": args.task,
        "task_id": args.task_id,
        "prompt": prompt,
        "pid": pid,
        "trello_card_id": card_id,
        "status": "active",
        "launched_at": _now_iso(),
        "last_checkin": None,
        "checkins": [],
        "context_resets": 0,
        "completed_at": None,
        "summary": None
    }
    tracker["tabs"].append(tab)
    _save_tracker(tracker)

    print(f"\n✅ Tab tracked: {tab_id}")
    print(f"   PID: {pid or 'not detected yet'}")
    print(f"   Trello: {card_id or 'failed'}")
    return tab_id


def cmd_status(args):
    """Show status of active tabs."""
    tracker = _load_tracker()
    active = [t for t in tracker["tabs"] if t["status"] == "active"]

    if not active:
        print("No active Claude Code tabs.")
        return

    for tab in active:
        pid = _find_pid(tab["project"])
        jsonl, mtime = _get_latest_jsonl(tab["project"])

        # Detect stalls
        stale_mins = 0
        if mtime > 0:
            stale_mins = (time.time() - mtime) / 60

        status_icon = "🟢"
        if pid is None:
            status_icon = "🔴 DEAD"
        elif stale_mins > 15:
            status_icon = "🟡 STALE"

        lines = _transcript_line_count(jsonl) if jsonl else 0

        print(f"\n{status_icon} {tab['id']} — {tab['project_name']}")
        print(f"  Task: {tab['task']}")
        print(f"  PID: {pid or 'NOT FOUND'}")
        print(f"  Launched: {tab['launched_at']}")
        print(f"  Last checkin: {tab['last_checkin'] or 'never'}")
        print(f"  Context resets: {tab['context_resets']}")
        print(f"  Transcript: {lines} lines, {stale_mins:.0f}m since last activity")
        if tab.get("checkins"):
            last = tab["checkins"][-1]
            print(f"  Last update: [{last['status']}] {last['detail']}")


def cmd_monitor(args):
    """Monitor all active tabs — detect stalls, dead processes, missing checkins."""
    tracker = _load_tracker()
    active = [t for t in tracker["tabs"] if t["status"] == "active"]
    issues = []

    for tab in active:
        pid = _find_pid(tab["project"])
        jsonl, mtime = _get_latest_jsonl(tab["project"])

        # Process dead?
        if pid is None:
            issues.append(f"🔴 {tab['id']} ({tab['project_name']}): Process not found. May have finished or crashed.")
            # Update tracker
            tab["pid"] = None

        # Transcript stale?
        if mtime > 0:
            stale_mins = (time.time() - mtime) / 60
            if stale_mins > 30:
                issues.append(f"🟡 {tab['id']} ({tab['project_name']}): No transcript activity for {stale_mins:.0f}m.")

        # No checkin in a while?
        if tab.get("last_checkin"):
            last_ts = datetime.fromisoformat(tab["last_checkin"])
            mins_since = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60
            if mins_since > 60:
                issues.append(f"⚠️ {tab['id']} ({tab['project_name']}): No checkin for {mins_since:.0f}m.")
        elif tab.get("launched_at"):
            launched = datetime.fromisoformat(tab["launched_at"])
            mins_since = (datetime.now(timezone.utc) - launched).total_seconds() / 60
            if mins_since > 30:
                issues.append(f"⚠️ {tab['id']} ({tab['project_name']}): Never checked in ({mins_since:.0f}m since launch).")

    _save_tracker(tracker)

    if issues:
        print("CLAUDE_TAB_ISSUES")
        for issue in issues:
            print(issue)
    else:
        print("All tabs healthy.")


def cmd_checkin(args):
    """Record a checkin from Claude Code (called when processing openclaw-checkin.py messages)."""
    tracker = _load_tracker()

    # Find matching tab by project name or task ID
    for tab in tracker["tabs"]:
        if tab["status"] != "active":
            continue
        match = False
        if args.project and args.project.lower() in tab["project_name"].lower():
            match = True
        if args.task_id and tab.get("task_id") == args.task_id:
            match = True
        if match:
            checkin = {
                "timestamp": _now_iso(),
                "status": args.checkin_status,
                "detail": args.detail or "",
                "task": args.task_id or ""
            }
            tab["checkins"].append(checkin)
            tab["last_checkin"] = checkin["timestamp"]

            # Update Trello card with comment
            if tab.get("trello_card_id"):
                _trello_comment(
                    tab["trello_card_id"],
                    f"**Checkin [{args.checkin_status}]:** {args.detail or 'No details'}"
                )

            _save_tracker(tracker)
            print(f"Checkin recorded for {tab['id']}: [{args.checkin_status}] {args.detail}")
            return

    print(f"WARNING: No matching active tab for project={args.project} task={args.task_id}", file=sys.stderr)


def cmd_verify(args):
    """Verify that a tab's work is complete."""
    tracker = _load_tracker()

    tab = next((t for t in tracker["tabs"] if t["id"] == args.tab_id), None)
    if not tab:
        print(f"Tab {args.tab_id} not found.")
        return

    print(f"Verifying: {tab['project_name']} — {tab['task']}")

    # Check if process is still running
    pid = _find_pid(tab["project"])
    if pid:
        print(f"⚠️ Claude Code still running (PID {pid}). May not be done yet.")

    # Check TODO.md in project
    todo_path = os.path.join(tab["project"], "TODO.md")
    if os.path.exists(todo_path):
        with open(todo_path) as f:
            content = f.read()
        unchecked = content.count("- [ ]")
        checked = content.count("- [x]")
        print(f"TODO.md: {checked} done, {unchecked} remaining")
        if unchecked > 0:
            print(f"⚠️ {unchecked} unchecked items remain in TODO.md")
    else:
        print("No TODO.md found in project.")

    # Check git status
    try:
        result = subprocess.run(
            ["git", "-C", tab["project"], "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=10
        )
        print(f"\nRecent commits:")
        print(result.stdout)
    except Exception:
        pass

    # Check dm/todo.md if it exists (openclaw-dm specific)
    dm_todo = os.path.join(tab["project"], "dm", "todo.md")
    if os.path.exists(dm_todo):
        with open(dm_todo) as f:
            content = f.read()
        unchecked = content.count("- [ ]")
        print(f"dm/todo.md: {unchecked} unchecked items")


def cmd_close(args):
    """Close a tab — mark complete, update Trello."""
    tracker = _load_tracker()

    tab = next((t for t in tracker["tabs"] if t["id"] == args.tab_id), None)
    if not tab:
        print(f"Tab {args.tab_id} not found.")
        return

    # Kill process if still running
    pid = _find_pid(tab["project"])
    if pid:
        print(f"Killing Claude Code process (PID {pid})...")
        try:
            subprocess.run(["kill", str(pid)], timeout=5)
        except Exception:
            pass

    # Update tracker
    tab["status"] = "completed"
    tab["completed_at"] = _now_iso()
    tab["summary"] = args.summary or "Completed"
    tab["pid"] = None

    # Update Trello card
    if tab.get("trello_card_id"):
        _trello_update_card(tab["trello_card_id"], dueComplete="true")
        _trello_comment(
            tab["trello_card_id"],
            f"✅ **Closed by Coconut**\n\n{args.summary or 'Work verified complete.'}"
        )

    _save_tracker(tracker)
    print(f"✅ Tab {args.tab_id} closed: {tab['project_name']} — {tab['task']}")


def cmd_list(args):
    """List all tabs (active + completed)."""
    tracker = _load_tracker()

    active = [t for t in tracker["tabs"] if t["status"] == "active"]
    completed = [t for t in tracker["tabs"] if t["status"] == "completed"]

    if active:
        print("=== Active ===")
        for t in active:
            print(f"  🟢 {t['id']} | {t['project_name']} | {t['task']} | launched: {t['launched_at']}")

    if completed:
        print("\n=== Completed ===")
        for t in completed:
            print(f"  ✅ {t['id']} | {t['project_name']} | {t['task']} | {t.get('summary', '')}")

    if not active and not completed:
        print("No tabs tracked yet.")


def main():
    parser = argparse.ArgumentParser(description="Claude Code tab manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # launch
    p = sub.add_parser("launch", help="Launch and track a new Claude Code tab")
    p.add_argument("--project", required=True, help="Project directory")
    p.add_argument("--task", required=True, help="Task description")
    p.add_argument("--task-id", help="Task ID (e.g. T001)")
    p.add_argument("--prompt", help="Custom prompt (defaults to task)")

    # status
    p = sub.add_parser("status", help="Show status of active tabs")
    p.add_argument("--tab-id", help="Specific tab ID")

    # monitor
    sub.add_parser("monitor", help="Monitor tabs, detect issues")

    # checkin
    p = sub.add_parser("checkin", help="Record a Claude Code checkin")
    p.add_argument("--project", help="Project name")
    p.add_argument("--task-id", help="Task ID")
    p.add_argument("--checkin-status", required=True,
                   choices=["done", "blocked", "progress", "tests", "error"])
    p.add_argument("--detail", help="Detail text")

    # verify
    p = sub.add_parser("verify", help="Verify tab work is complete")
    p.add_argument("--tab-id", required=True, help="Tab ID to verify")

    # close
    p = sub.add_parser("close", help="Close a tab (mark complete)")
    p.add_argument("--tab-id", required=True, help="Tab ID to close")
    p.add_argument("--summary", help="Completion summary")

    # list
    sub.add_parser("list", help="List all tabs")

    args = parser.parse_args()
    cmd_map = {
        "launch": cmd_launch, "status": cmd_status, "monitor": cmd_monitor,
        "checkin": cmd_checkin, "verify": cmd_verify, "close": cmd_close,
        "list": cmd_list
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
