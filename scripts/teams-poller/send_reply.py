#!/usr/bin/env python3
"""Send a reply to Teams chat.

Usage:
    echo "reply text" | python3 send_reply.py
    python3 send_reply.py "reply text"
"""

import sys
import os
import re

# Add script dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poll_teams import load_config, load_state, save_state, BOT_SIGNATURE


def md_to_html(text):
    """Convert common markdown to Teams-compatible HTML."""
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    for line in lines:
        # Code block fences
        if line.strip().startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre>')
                in_code_block = True
            continue
        if in_code_block:
            html_lines.append(line)
            continue
        # Bold: **text** → <strong>text</strong>
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        # Italic: *text* → <em>text</em> (but not inside <strong>)
        line = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', line)
        # Inline code: `text` → <code>text</code>
        line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
        # Bullet lists: • or - at start
        if re.match(r'^\s*[•\-]\s+', line):
            line = re.sub(r'^\s*[•\-]\s+', '• ', line)
        # Empty line → paragraph break
        if line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(line)
    if in_code_block:
        html_lines.append('</pre>')
    return '<br>'.join(html_lines)

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
    clean_reply = re.sub(r'(\n\n|\s*)' + re.escape(bot_signature) + r'\s*$', '', reply_text).rstrip()
    # Convert markdown to Teams-compatible HTML
    reply_html = md_to_html(clean_reply)
    signed = f"{reply_html}<br><br><i>{bot_signature}</i>"
    body_html = signed
    mentions = []

    teams.send_chat_message(client, chat_id, body_html, mentions=mentions)
    print("Reply sent successfully")

    # Clear pending
    state["pending_reply"] = None
    save_state(state)


if __name__ == "__main__":
    main()
