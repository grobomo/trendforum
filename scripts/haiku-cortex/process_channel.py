#!/usr/bin/env python3
"""
Haiku Sensory Cortex — Channel Processor

Pulls raw messages from a channel since last-seen timestamp,
sends them to Haiku for summarization, and updates:
  1. memory/channels/<channel>.md (source of truth)
  2. Trello Comm Tracking card (visibility mirror)
  3. memory/channel-state.json (last-seen timestamp)

Usage:
  python3 process_channel.py --channel slack [--since <ts>]
  python3 process_channel.py --channel all
"""

import argparse
import json
import os
import sys
import keyring
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
CHANNELS_DIR = WORKSPACE / "memory" / "channels"
STATE_FILE = WORKSPACE / "memory" / "channel-state.json"

# Trello card IDs for Comm Tracking board
TRELLO_CARDS = {
    "email": "69e3e03b6cd9b22e36f7e441",
    "teams": "69e3e03b8cf6358ddc0939e5",
    "github": "69e3e03cbba0f57151a5ce5c",
    "slack": "69e3e03c8ec1f34110747b5d",
    "trello": "69e3e03defe4e70a38d0bece",
}

# Slack channel IDs
SLACK_CHANNELS = {
    "all-misfits": "C0ATFDQRGRL",
    "coco-chat": "C0ATJE19YRY",
    "social": "C0ATB4AS9PD",
    "joel-dm": "D0ATWPM4DTK",
}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"lastSeen": {}, "updatedAt": None}


def save_state(state):
    state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def update_trello_card(channel_name, description):
    """Update the Trello Comm Tracking card for this channel."""
    card_id = TRELLO_CARDS.get(channel_name)
    if not card_id:
        return
    
    try:
        api_key = keyring.get_password("openclaw", "TRELLO_API_KEY")
        token = keyring.get_password("openclaw", "TRELLO_TOKEN")
        
        data = urllib.parse.urlencode({
            "key": api_key,
            "token": token,
            "desc": description,
        }).encode()
        
        req = urllib.request.Request(
            f"https://api.trello.com/1/cards/{card_id}",
            data=data,
            method="PUT",
        )
        urllib.request.urlopen(req)
        print(f"  Trello card updated: {channel_name}")
    except Exception as e:
        print(f"  Trello update failed (non-blocking): {e}")


def update_channel_memory(channel_name, summary):
    """Write the Haiku-generated summary to the channel memory file."""
    channel_file = CHANNELS_DIR / f"{channel_name}.md"
    channel_file.write_text(summary)
    print(f"  Channel memory updated: {channel_file}")


def main():
    parser = argparse.ArgumentParser(description="Haiku Sensory Cortex")
    parser.add_argument("--channel", required=True, help="Channel to process (slack|teams|github|email|trello|all)")
    parser.add_argument("--since", help="Override last-seen timestamp")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing")
    args = parser.parse_args()

    if args.channel == "all":
        channels = ["slack", "teams", "github", "email", "trello"]
    else:
        channels = [args.channel]

    state = load_state()
    
    for channel in channels:
        print(f"\nProcessing: {channel}")
        print(f"  Last seen: {state['lastSeen'].get(f'slack:{channel}', {}).get('ts', 'never')}")
        
        # Channel-specific processing would go here
        # For now, this script handles the state management and Trello sync
        # The actual Haiku summarization is done via OpenClaw sessions_spawn
        
        channel_file = CHANNELS_DIR / f"{channel}.md"
        if channel_file.exists():
            content = channel_file.read_text()
            if not args.dry_run:
                update_trello_card(channel, content)
        else:
            print(f"  No channel memory file found: {channel_file}")

    if not args.dry_run:
        save_state(state)
    
    print("\nDone.")


if __name__ == "__main__":
    main()
