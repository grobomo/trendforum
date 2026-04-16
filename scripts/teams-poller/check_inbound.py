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
        # Clear the queue
        with open(INBOUND_QUEUE, "w") as f:
            json.dump(None, f)
except (FileNotFoundError, json.JSONDecodeError, TypeError):
    pass
