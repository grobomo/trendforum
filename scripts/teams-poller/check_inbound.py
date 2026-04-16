#!/usr/bin/env python3
"""Check for inbound Teams messages queued by the service.

Called by openclaw cron. Prints the prompt if there's a message waiting.
"""
import json
import sys
from pathlib import Path

INBOUND_QUEUE = Path.home() / ".openclaw" / "teams-poller" / "inbound_queue.json"

try:
    with open(INBOUND_QUEUE) as f:
        entry = json.load(f)
    if entry and entry.get("prompt"):
        print(entry["prompt"])
        # Save chat_id for queue_reply to use
        chat_id = entry.get("chat_id", "")
        if chat_id:
            LAST_CHAT = INBOUND_QUEUE.parent / "last_inbound_chat.json"
            with open(LAST_CHAT, "w") as f:
                json.dump({"chat_id": chat_id}, f)
        # Clear the queue
        with open(INBOUND_QUEUE, "w") as f:
            json.dump(None, f)
except (FileNotFoundError, json.JSONDecodeError, TypeError):
    pass
