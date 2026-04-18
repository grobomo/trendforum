#!/usr/bin/env python3
"""Queue a reply for the Teams service to post.

Usage:
    python3 queue_reply.py "reply text"
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
OUTBOUND_QUEUE = Path.home() / ".openclaw" / "teams-poller" / "outbound_queue.json"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_chat_access(config: dict, chat_id: str) -> str:
    """Return access policy for a chat_id ('read-only' or 'read-write')."""
    for c in config.get("chats", []):
        if c.get("id") == chat_id:
            return c.get("access", "read-write")
    return "read-write"


if len(sys.argv) > 1:
    reply = " ".join(sys.argv[1:])
else:
    reply = sys.stdin.read().strip()

if reply and reply != "TEAMS_NO_REPLY":
    OUTBOUND_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    # Check if there's a pending inbound with a chat_id to reply to
    target_chat_id = ""
    try:
        with open(OUTBOUND_QUEUE.parent / "last_inbound_chat.json") as f:
            target_chat_id = json.load(f).get("chat_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # SAFETY: block replies to read-only chats
    config = load_config()
    if target_chat_id and get_chat_access(config, target_chat_id) == "read-only":
        chat_label = next(
            (c.get("label", "?") for c in config.get("chats", []) if c.get("id") == target_chat_id),
            "unknown"
        )
        print(f"BLOCKED: cannot post to read-only chat '{chat_label}'. Relay to Joel via Slack DM instead.")
        sys.exit(1)

    with open(OUTBOUND_QUEUE, "w") as f:
        json.dump({
            "reply": reply,
            "chat_id": target_chat_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)
    print("Reply queued for posting")
else:
    print("No reply to queue")
