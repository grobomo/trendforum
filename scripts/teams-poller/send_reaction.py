#!/usr/bin/env python3
"""Send a reaction to a Teams chat message.

Usage:
    python3 send_reaction.py --chat-id <chat_id> --message-id <msg_id> --reaction <type>
    python3 send_reaction.py --chat <label> --message-id <msg_id> --reaction <type>

Reaction types: like, heart, laugh, surprised, sad, angry

Use --remove to unset a reaction instead.
"""

import argparse
import json
import os
import sys

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient
from lib.msgraph import teams


def get_chat_id_by_label(label: str) -> str:
    """Look up chat ID from config.json by label (case-insensitive partial match)."""
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    label_lower = label.lower()
    for chat in config.get("chats", []):
        if label_lower in chat.get("label", "").lower():
            return chat["id"]
    raise ValueError(f"No chat found matching label '{label}'")


def main():
    parser = argparse.ArgumentParser(description="Send a reaction to a Teams message")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--chat-id", help="Teams chat ID")
    group.add_argument("--chat", help="Chat label (from config.json)")
    parser.add_argument("--message-id", required=True, help="Message ID to react to")
    parser.add_argument("--reaction", required=True,
                        choices=["like", "heart", "laugh", "surprised", "sad", "angry"],
                        help="Reaction type")
    parser.add_argument("--remove", action="store_true", help="Remove reaction instead of setting it")
    args = parser.parse_args()

    chat_id = args.chat_id or get_chat_id_by_label(args.chat)

    token_mgr = TokenManager()
    token = token_mgr.get_token()
    client = GraphClient(token=token)

    try:
        if args.remove:
            teams.unset_reaction(client, chat_id, args.message_id, args.reaction)
            print(f"Removed '{args.reaction}' from message {args.message_id}")
        else:
            teams.set_reaction(client, chat_id, args.message_id, args.reaction)
            print(f"Reacted '{args.reaction}' to message {args.message_id}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
