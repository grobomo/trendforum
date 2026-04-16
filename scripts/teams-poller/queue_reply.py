#!/usr/bin/env python3
"""Queue a reply for the Teams service to post.

Usage:
    python3 queue_reply.py "reply text"
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTBOUND_QUEUE = Path.home() / ".openclaw" / "teams-poller" / "outbound_queue.json"

if len(sys.argv) > 1:
    reply = " ".join(sys.argv[1:])
else:
    reply = sys.stdin.read().strip()

if reply and reply != "TEAMS_NO_REPLY":
    OUTBOUND_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    # Check if there's a pending inbound with a chat_id to reply to
    INBOUND_QUEUE = OUTBOUND_QUEUE.parent / "inbound_queue.json"
    target_chat_id = ""
    try:
        with open(INBOUND_QUEUE.parent / "last_inbound_chat.json") as f:
            target_chat_id = json.load(f).get("chat_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    with open(OUTBOUND_QUEUE, "w") as f:
        json.dump({
            "reply": reply,
            "chat_id": target_chat_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)
    print("Reply queued for posting")
else:
    print("No reply to queue")
