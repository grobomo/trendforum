#!/usr/bin/env python3
"""Check Teams tracker for gaps and output structured prompt for agent to act on.

Designed for heartbeat/cron: produces output ONLY when there are gaps to fill.
No output = nothing to do.

Usage:
    python3 check_gaps.py [--minutes 10] [--enriched]

With --enriched, fetches actual message content from Graph API for pending
messages that only have webhook stubs (sender=unknown, no preview).
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Add tracker to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from teams_tracker.tracker import TeamsTracker

# Config for chat access policies
CONFIG_FILE = SCRIPT_DIR.parent / "teams-poller" / "config.json"


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def get_access(chat_id: str, config: dict) -> str:
    """Get access level for a chat from config."""
    for c in config.get("chats", []):
        if c.get("id") == chat_id:
            return c.get("access", "unknown")
    return "unknown"


def enrich_from_graph(tracker: TeamsTracker, config: dict):
    """Fetch actual message content for webhook stubs that have no preview/sender."""
    msgraph_lib = os.path.expanduser("~/lib/teams-agent")
    if msgraph_lib not in sys.path:
        sys.path.insert(0, msgraph_lib)

    try:
        from lib.msgraph.auth import TokenManager
        from lib.msgraph.client import GraphClient
        from lib.msgraph import teams
    except ImportError:
        log.warning("Graph API libs not available for enrichment")
        return

    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.warning("No Graph token for enrichment")
        return

    client = GraphClient(token=token)

    # Find stubs that need enrichment (unknown sender or empty preview)
    stubs = [m for m in tracker.pending()
             if m.get("sender") == "unknown" or not m.get("preview")]

    if not stubs:
        return

    # Group by chat to minimize API calls
    by_chat = {}
    for s in stubs:
        by_chat.setdefault(s["chat_id"], []).append(s)

    bot_signature = config.get("bot_signature", "--coconut-bot")

    for chat_id, msgs in by_chat.items():
        try:
            raw = teams.get_chat_messages(client, chat_id, top=10,
                                          order_by="createdDateTime desc")
        except Exception as e:
            log.warning("Enrich failed for %s: %s", chat_id, e)
            continue

        # Build lookup of msg_id → parsed message
        graph_msgs = {}
        for m in raw:
            p = teams.parse_message(m)
            mid = p.get("message_id", "")
            if mid:
                graph_msgs[mid] = p

        # Update stubs with real data
        for stub in msgs:
            real = graph_msgs.get(stub["msg_id"])
            if real and real.get("sender_name"):
                key = f"{stub['chat_id']}:{stub['msg_id']}"
                text = real.get("text", "")
                # Auto-mark bot messages as responded (delegated auth shows as Joel)
                if bot_signature in text:
                    if key in tracker.data["pending"]:
                        del tracker.data["pending"][key]
                    continue
                if key in tracker.data["pending"]:
                    entry = tracker.data["pending"][key]
                    entry["sender"] = real["sender_name"]
                    entry["preview"] = text[:120]
                    entry["source"] = f"{entry.get('source', 'webhook')}+enriched"

    tracker._save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=10,
                        help="Only report messages older than N minutes")
    parser.add_argument("--enriched", action="store_true",
                        help="Fetch content from Graph for webhook stubs")
    args = parser.parse_args()

    config = load_config()
    tracker = TeamsTracker()

    if args.enriched:
        enrich_from_graph(tracker, config)

    stale = tracker.stale(minutes=args.minutes)
    if not stale:
        return  # Nothing to do — silent exit

    bot_signature = config.get("bot_signature", "--coconut-bot")
    # Filter out bot's own messages (delegated auth shows sender as Joel)
    stale = [m for m in stale if bot_signature not in m.get("preview", "")]
    if not stale:
        return

    # Group by chat — include ALL monitored chats (skip only disabled)
    rw_chats = {}   # read-write: compose and send replies
    ro_chats = {}   # read-only/unknown: flag important content to Joel
    for m in stale:
        chat_id = m["chat_id"]
        access = get_access(chat_id, config)
        if access == "disabled":
            continue  # Only skip explicitly disabled chats
        label = m.get("label", chat_id[:20])
        bucket = rw_chats if access == "read-write" else ro_chats
        bucket.setdefault(label, {"chat_id": chat_id, "access": access, "msgs": []})
        bucket[label]["msgs"].append(m)

    if not rw_chats and not ro_chats:
        return  # Nothing pending

    # Output structured prompt for agent
    print("TEAMS_GAPS_FOUND")
    print(f"Chats with unanswered messages (>{args.minutes}m):")

    if rw_chats:
        print()
        print("=== READ-WRITE (compose and send reply) ===")
        for label, info in rw_chats.items():
            _print_chat(label, info, tracker)

    if ro_chats:
        print()
        print("=== READ-ONLY (flag important content to Joel via Slack DM) ===")
        for label, info in ro_chats.items():
            _print_chat(label, info, tracker)

    print()
    print("ACTIONS:")
    if rw_chats:
        print("  - Read-write chats: compose and send replies via queue_reply.py, then mark responded")
    if ro_chats:
        print("  - Read-only chats: flag anything important/actionable to Joel via Slack DM")


def _print_chat(label, info, tracker):
    msgs = info["msgs"]
    print(f"  [{label}] ({len(msgs)} pending, access: {info['access']}, chat_id: {info['chat_id']})")
    for m in msgs[-3:]:  # Show last 3 per chat
        age_min = (tracker._now_epoch_static() - m["recorded_at"]) / 60
        sender = m.get("sender", "unknown")
        preview = m.get("preview", "(no preview)")
        print(f"    - {sender} ({age_min:.0f}m ago): {preview}")
    if len(msgs) > 3:
        print(f"    ... and {len(msgs) - 3} more")


# Static epoch for age calculation (avoid instance method dependency)
TeamsTracker._now_epoch_static = staticmethod(lambda: __import__("time").time())

if __name__ == "__main__":
    main()
