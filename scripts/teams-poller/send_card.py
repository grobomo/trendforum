#!/usr/bin/env python3
"""Send an Adaptive Card to a Teams chat.

Usage:
    python3 send_card.py <chat_alias_or_id> [--demo]
    echo '{"title":"Test","body":"Hello"}' | python3 send_card.py <chat_alias_or_id>

The card JSON should have:
    title: Header text
    body: Main content (plain text or markdown-ish)
    sections: Optional list of collapsible sections [{title, content}]
    actions: Optional list of action buttons [{title, url}]
    facts: Optional list of key-value pairs [{key, value}]
    accent: Optional accent color hex (default: palm tree green #2E8B57)
"""

import json
import os
import sys
from pathlib import Path

# Add script dir + msgraph lib
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient

# ── Config ───────────────────────────────────────────────────────────

CONFIG_FILE = SCRIPT_DIR / "config.json"
PALM_GREEN = "#2E8B57"
BOT_SIGNATURE = "--coconut-bot"


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def resolve_chat_id(alias_or_id, config):
    """Resolve a chat alias or label to a chat ID."""
    for chat in config.get("chats", []):
        if alias_or_id in (chat.get("id"), chat.get("label"), chat.get("alias", "")):
            return chat["id"], chat.get("label", alias_or_id)
    # If no match, treat as raw chat ID
    return alias_or_id, alias_or_id


def build_adaptive_card(data, accent_color=PALM_GREEN):
    """Build an Adaptive Card JSON from structured data.

    Args:
        data: dict with title, body, sections, actions, facts, accent
        accent_color: hex color for accent elements
    """
    accent = data.get("accent", accent_color)

    card_body = []

    # ── Header with accent bar ──
    header_columns = [
        # Accent bar (thin colored column)
        {
            "type": "Column",
            "width": "8px",
            "items": [
                {
                    "type": "TextBlock",
                    "text": " ",
                    "wrap": True,
                }
            ],
            "style": "good",  # Green tint
            "bleed": True,
        },
        # Title
        {
            "type": "Column",
            "width": "stretch",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"🌴 {data.get('title', 'Coconut')}",
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Good",
                    "wrap": True,
                }
            ],
            "verticalContentAlignment": "Center",
        }
    ]

    card_body.append({
        "type": "ColumnSet",
        "columns": header_columns,
    })

    # Separator
    card_body.append({
        "type": "TextBlock",
        "text": " ",
        "spacing": "Small",
        "separator": True,
    })

    # ── Main body ──
    if data.get("body"):
        card_body.append({
            "type": "TextBlock",
            "text": data["body"],
            "wrap": True,
            "spacing": "Medium",
        })

    # ── Facts (key-value pairs) ──
    if data.get("facts"):
        fact_items = [{"title": f.get("key", ""), "value": f.get("value", "")} for f in data["facts"]]
        card_body.append({
            "type": "FactSet",
            "facts": fact_items,
            "spacing": "Medium",
        })

    # ── Collapsible Sections ──
    # Note: Adaptive Cards don't have native collapsible sections in all clients.
    # We use Action.ShowCard to simulate collapsible behavior.
    if data.get("sections"):
        for section in data["sections"]:
            card_body.append({
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.ShowCard",
                        "title": f"▸ {section.get('title', 'Details')}",
                        "card": {
                            "type": "AdaptiveCard",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": section.get("content", ""),
                                    "wrap": True,
                                }
                            ],
                        },
                    }
                ],
            })

    # ── Signature ──
    card_body.append({
        "type": "TextBlock",
        "text": f"_{BOT_SIGNATURE}_ 🌴",
        "spacing": "Medium",
        "isSubtle": True,
        "size": "Small",
        "horizontalAlignment": "Right",
    })

    # ── Action buttons ──
    actions = []
    if data.get("actions"):
        for action in data["actions"]:
            actions.append({
                "type": "Action.OpenUrl",
                "title": action.get("title", "Open"),
                "url": action.get("url", "#"),
            })

    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": card_body,
    }
    if actions:
        card["actions"] = actions

    # MSTeams-specific: accent color via msteams property
    card["msteams"] = {
        "width": "Full",
    }

    return card


def send_card(client, chat_id, card_json, summary="Coconut Card"):
    """Send an Adaptive Card via Graph API."""
    payload = {
        "body": {
            "contentType": "html",
            "content": f'<attachment id="coconut-card"></attachment>',
        },
        "attachments": [
            {
                "id": "coconut-card",
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": json.dumps(card_json),
                "name": summary,
            }
        ],
    }
    return client.post(f"/me/chats/{chat_id}/messages", body=payload)


def demo_card():
    """Build a demo card showing off features."""
    return {
        "title": "Adaptive Card Prototype",
        "body": "This is a demo of Coconut's new card format. Palm tree green accent, structured layout, collapsible sections.",
        "facts": [
            {"key": "Status", "value": "✅ Online"},
            {"key": "Channel", "value": "Coconut Private"},
            {"key": "Accent", "value": "Palm Tree Green (#2E8B57)"},
        ],
        "sections": [
            {
                "title": "Edge Case Analysis",
                "content": "• **Orphaned alias** — chat deleted but alias exists\n• **Unregistered chat** — no alias for new group\n• **Duplicate aliases** — config points two aliases at same chat\n• **Stale lock** — process crashes, lock never released",
            },
            {
                "title": "Email Triage Example",
                "content": "**From:** Dan Toresi (Entertainment Partners)\n**Subject:** MDR Alert - Suspicious Lateral Movement\n**Priority:** 🔴 High\n\nDetected at 14:32 CDT. Source: EP-WKS-0847. Destination: DC-PROD-02. Recommend immediate investigation.",
            },
        ],
        "actions": [
            {"title": "📋 View Trello Board", "url": "https://trello.com/b/TyFBN1Bx/to-do-list"},
            {"title": "📧 Open Email", "url": "https://outlook.office.com"},
        ],
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 send_card.py <chat_alias_or_id> [--demo]", file=sys.stderr)
        sys.exit(1)

    chat_target = sys.argv[1]
    is_demo = "--demo" in sys.argv

    config = load_config()
    chat_id, label = resolve_chat_id(chat_target, config)

    if not chat_id:
        print(f"Could not resolve chat: {chat_target}", file=sys.stderr)
        sys.exit(1)

    # Get card data
    if is_demo:
        card_data = demo_card()
    elif not sys.stdin.isatty():
        card_data = json.loads(sys.stdin.read())
    else:
        print("Provide card JSON via stdin or use --demo", file=sys.stderr)
        sys.exit(1)

    # Build card
    card_json = build_adaptive_card(card_data)

    # Auth
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        print("No valid Graph token", file=sys.stderr)
        sys.exit(1)

    client = GraphClient(token=token)

    # Send
    print(f"Sending card to {label} ({chat_id})...")
    result = send_card(client, chat_id, card_json, summary=card_data.get("title", "Coconut Card"))
    print(f"✅ Card sent! Message ID: {result.get('id', 'unknown')}")

    return result


if __name__ == "__main__":
    main()
