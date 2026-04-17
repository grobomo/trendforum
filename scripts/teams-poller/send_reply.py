#!/usr/bin/env python3
"""Send a reply to Teams chat.

Usage:
    echo "reply text" | python3 send_reply.py
    python3 send_reply.py "reply text"
"""

import sys
import os

# Add script dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poll_teams import load_config, load_state, save_state, BOT_SIGNATURE

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient
from lib.msgraph import teams


def main():
    # Get reply text from args or stdin
    if len(sys.argv) > 1:
        reply_text = " ".join(sys.argv[1:])
    else:
        reply_text = sys.stdin.read().strip()

    if not reply_text:
        print("No reply text provided", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    state = load_state()
    chat_id = config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)
    pending = state.get("pending_reply")

    if not chat_id:
        print("No chat_id in config", file=sys.stderr)
        sys.exit(1)

    # Auth
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        print("No valid Graph token", file=sys.stderr)
        sys.exit(1)
    client = GraphClient(token=token)

    # Build reply — no @mention prefix, just the reply text + signature
    # Strip any existing bot signature from reply text to prevent duplicates
    import re
    clean_reply = re.sub(r'(\n\n|\s*)' + re.escape(bot_signature) + r'\s*$', '', reply_text).rstrip()
    signed = f"{clean_reply}\n\n<i>{bot_signature}</i>"
    body_html = signed
    mentions = []

    teams.send_chat_message(client, chat_id, body_html, mentions=mentions)
    print("Reply sent successfully")

    # Clear pending
    state["pending_reply"] = None
    save_state(state)


if __name__ == "__main__":
    main()
