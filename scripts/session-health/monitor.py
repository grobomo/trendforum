#!/usr/bin/env python3
"""
Session Health Monitor

Checks main session size and compaction count.
Auto-resets when thresholds are exceeded.

Thresholds:
- Session file > 5MB → WARNING
- Session file > 15MB → AUTO-RESET
- Compaction count > 15 → AUTO-RESET
- sessions.json > 10MB → AUTO-CLEANUP stale entries
- Orphaned .tmp/.deleted files → AUTO-CLEANUP

Usage:
    python3 monitor.py          # Check + auto-fix
    python3 monitor.py --check  # Check only, no fixes
    python3 monitor.py --force-reset  # Force reset main session now
"""

import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime, timezone

SESSIONS_DIR = os.path.expanduser("~/.openclaw/agents/main/sessions")
SESSIONS_JSON = os.path.join(SESSIONS_DIR, "sessions.json")
ARCHIVE_DIR = os.path.expanduser("~/.openclaw/workspace/.archive/sessions")

# Thresholds
WARN_SIZE_MB = 5
RESET_SIZE_MB = 15
MAX_COMPACTIONS = 15
SESSIONS_JSON_MAX_MB = 10
STALE_SESSION_HOURS = 72


def get_main_session():
    """Find the main session from sessions.json."""
    if not os.path.exists(SESSIONS_JSON):
        return None, None

    with open(SESSIONS_JSON) as f:
        sessions = json.load(f)

    main = sessions.get("agent:main:main")
    if not main:
        return None, None

    session_id = main.get("sessionId")
    session_file = main.get("sessionFile")
    compactions = main.get("compactionCount", 0)

    if not session_file or not os.path.exists(session_file):
        # Try to find it
        pattern = os.path.join(SESSIONS_DIR, f"{session_id}*.jsonl")
        matches = glob.glob(pattern)
        if matches:
            session_file = matches[0]
        else:
            return None, None

    return {
        "id": session_id,
        "file": session_file,
        "size_bytes": os.path.getsize(session_file),
        "size_mb": os.path.getsize(session_file) / (1024 * 1024),
        "compactions": compactions,
    }, main


def check_orphans():
    """Find orphaned .tmp and .deleted files."""
    orphans = []
    for f in os.listdir(SESSIONS_DIR):
        full = os.path.join(SESSIONS_DIR, f)
        if f.endswith(".tmp") or ".deleted." in f or ".checkpoint." in f:
            orphans.append({
                "file": full,
                "size_mb": os.path.getsize(full) / (1024 * 1024),
            })
    return orphans


def check_sessions_json_size():
    """Check sessions.json size."""
    if not os.path.exists(SESSIONS_JSON):
        return 0
    return os.path.getsize(SESSIONS_JSON) / (1024 * 1024)


def archive_session(session_info):
    """Archive a session file."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    src = session_info["file"]
    basename = os.path.basename(src)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(ARCHIVE_DIR, f"{timestamp}-{basename}")
    shutil.move(src, dest)
    return dest


def reset_main_session(session_info, main_entry):
    """Reset the main session: archive file, remove from sessions.json."""
    # Archive the session file
    dest = archive_session(session_info)

    # Remove from sessions.json
    with open(SESSIONS_JSON) as f:
        sessions = json.load(f)

    if "agent:main:main" in sessions:
        del sessions["agent:main:main"]

    with open(SESSIONS_JSON, "w") as f:
        json.dump(sessions, f, indent=2)

    return dest


def cleanup_orphans(orphans):
    """Remove orphaned files."""
    removed = []
    for orphan in orphans:
        os.remove(orphan["file"])
        removed.append(orphan["file"])
    return removed


def cleanup_stale_sessions():
    """Remove stale entries from sessions.json."""
    if not os.path.exists(SESSIONS_JSON):
        return 0

    with open(SESSIONS_JSON) as f:
        sessions = json.load(f)

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - (STALE_SESSION_HOURS * 3600 * 1000)

    original = len(sessions)
    kept = {}
    for key, val in sessions.items():
        updated = val.get("updatedAt", 0)
        # Keep: recent, active channels, crons, main
        is_recent = updated > cutoff_ms
        is_channel = "slack:channel:" in key and ":thread:" not in key
        is_important = any(k in key for k in ["cron", "dreaming", "main"])

        if is_recent or is_channel or is_important:
            kept[key] = val

    if len(kept) < original:
        with open(SESSIONS_JSON, "w") as f:
            json.dump(kept, f, indent=2)

    return original - len(kept)


def main():
    parser = argparse.ArgumentParser(description="Session Health Monitor")
    parser.add_argument("--check", action="store_true", help="Check only, no fixes")
    parser.add_argument("--force-reset", action="store_true", help="Force reset main session")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "actions": [],
        "warnings": [],
        "errors": [],
    }

    # 1. Check main session
    session_info, main_entry = get_main_session()

    if session_info:
        results["main_session"] = {
            "id": session_info["id"],
            "size_mb": round(session_info["size_mb"], 1),
            "compactions": session_info["compactions"],
        }

        if args.force_reset:
            if not args.check:
                dest = reset_main_session(session_info, main_entry)
                results["actions"].append(f"FORCE RESET: archived to {dest}")
                results["status"] = "reset"
            else:
                results["actions"].append("WOULD FORCE RESET (--check mode)")

        elif session_info["size_mb"] > RESET_SIZE_MB or session_info["compactions"] > MAX_COMPACTIONS:
            reason = []
            if session_info["size_mb"] > RESET_SIZE_MB:
                reason.append(f"size={session_info['size_mb']:.1f}MB > {RESET_SIZE_MB}MB")
            if session_info["compactions"] > MAX_COMPACTIONS:
                reason.append(f"compactions={session_info['compactions']} > {MAX_COMPACTIONS}")

            results["status"] = "critical"
            if not args.check:
                dest = reset_main_session(session_info, main_entry)
                results["actions"].append(f"AUTO-RESET ({', '.join(reason)}): archived to {dest}")
            else:
                results["errors"].append(f"NEEDS RESET: {', '.join(reason)}")

        elif session_info["size_mb"] > WARN_SIZE_MB:
            results["status"] = "warning"
            results["warnings"].append(
                f"Session size {session_info['size_mb']:.1f}MB approaching limit ({RESET_SIZE_MB}MB)"
            )
    else:
        results["main_session"] = None
        results["warnings"].append("No main session found (will be created on next interaction)")

    # 2. Check orphaned files
    orphans = check_orphans()
    if orphans:
        total_mb = sum(o["size_mb"] for o in orphans)
        if not args.check:
            removed = cleanup_orphans(orphans)
            results["actions"].append(f"Cleaned {len(orphans)} orphaned files ({total_mb:.1f}MB)")
        else:
            results["warnings"].append(f"{len(orphans)} orphaned files ({total_mb:.1f}MB)")

    # 3. Check sessions.json size
    sj_size = check_sessions_json_size()
    if sj_size > SESSIONS_JSON_MAX_MB:
        if not args.check:
            dropped = cleanup_stale_sessions()
            results["actions"].append(f"Cleaned {dropped} stale session entries from sessions.json")
        else:
            results["warnings"].append(f"sessions.json is {sj_size:.1f}MB (limit: {SESSIONS_JSON_MAX_MB}MB)")

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "🔴", "reset": "🔄"}
        print(f"{status_emoji.get(results['status'], '?')} Session Health: {results['status'].upper()}")

        if results.get("main_session"):
            ms = results["main_session"]
            print(f"  Main session: {ms['size_mb']}MB, {ms['compactions']} compactions")

        for w in results["warnings"]:
            print(f"  ⚠️ {w}")
        for e in results["errors"]:
            print(f"  🔴 {e}")
        for a in results["actions"]:
            print(f"  ✅ {a}")

        if not results["warnings"] and not results["errors"] and not results["actions"]:
            print("  All clear.")


if __name__ == "__main__":
    main()
