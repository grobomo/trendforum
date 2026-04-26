#!/usr/bin/env python3
"""Send a Teams message directly via Graph API, bypassing the outbound queue.

Usage:
    echo "message text" | python3 send_direct.py --chat-id 19:abc@thread.v2
    echo "message text" | python3 send_direct.py --chat "Coconut Private"
    echo "message text" | python3 send_direct.py --chat "Coconut Private" --style island

Applies per-chat style from config.json automatically (override with --style).
Verifies delivery via Graph API readback.
Message body comes from stdin ONLY.
"""
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
STYLES_DIR = SCRIPT_DIR / "styles"
PALM = "\U0001f334"
BOT_SIGNATURE = "--coconut-bot"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, os.path.expanduser("~/lib/teams-agent"))

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient


def load_config():
    try:
        return json.load(open(CONFIG_FILE))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def resolve_chat(config, target):
    """Resolve --chat label or --chat-id to (chat_id, chat_cfg)."""
    for c in config.get("chats", []):
        if c.get("id") == target:
            return c["id"], c
    # Label match (case-insensitive)
    for c in config.get("chats", []):
        if c.get("label", "").lower() == target.lower():
            return c["id"], c
    # Partial match
    for c in config.get("chats", []):
        if target.lower() in c.get("label", "").lower():
            return c["id"], c
    # Raw chat ID
    if target.startswith("19:"):
        return target, {}
    return None, None


def md_to_html(text):
    """Minimal markdown to HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = text.replace('\n', '<br>')
    return text


def enforce_bookends(text):
    if not text.startswith(PALM):
        text = f"{PALM} {text}"
    if not text.rstrip().endswith(PALM):
        text = f"{text.rstrip()} {PALM}"
    return text


def parse_topic_sections(text):
    """Parse [topic] tagged sections into list of (topic, content) tuples."""
    # Split on [topic] headers
    parts = re.split(r'\[([^\]]+)\]', text)
    sections = []
    if len(parts) < 3:
        # No topic tags found — return as single section
        return [(None, text.strip())]
    # parts[0] = preamble, then alternating topic/content
    preamble = parts[0].strip()
    if preamble:
        sections.append((None, preamble))
    for i in range(1, len(parts), 2):
        topic = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if topic and content:
            sections.append((topic, content))
    return sections if sections else [(None, text.strip())]


def build_sectioned_card(template, text):
    """Build adaptive card with [topic] sections as separate containers."""
    sections = parse_topic_sections(text)
    body_items = []
    for topic, content in sections:
        container_items = []
        if topic:
            container_items.append({
                "type": "TextBlock",
                "text": f"📋 {topic}",
                "weight": "bolder",
                "size": "medium",
                "color": "accent",
                "wrap": True,
                "spacing": "Small"
            })
        container_items.append({
            "type": "TextBlock",
            "text": content,
            "wrap": True,
            "spacing": "Small"
        })
        body_items.append({
            "type": "Container",
            "style": "emphasis",
            "spacing": "Medium",
            "items": container_items
        })
    # Build card from template skeleton
    card = json.loads(json.dumps(template))
    # Replace the body: keep header + spacer, insert sections, add footer
    new_body = [
        {"type": "TextBlock", "size": "medium", "text": " "},
        {
            "type": "Container",
            "style": "emphasis",
            "items": [{
                "type": "TextBlock",
                "color": "good",
                "size": "large",
                "text": "🌴 Coconut",
                "weight": "bolder",
                "wrap": True
            }]
        }
    ]
    new_body.extend(body_items)
    new_body.append({
        "type": "Container",
        "style": "emphasis",
        "items": [{
            "type": "TextBlock",
            "horizontalAlignment": "right",
            "isSubtle": True,
            "size": "small",
            "text": "_--coconut-bot_ 🌴",
            "spacing": "Medium"
        }]
    })
    new_body.append({"type": "TextBlock", "size": "medium", "text": " "})
    card["body"] = new_body
    return card


def apply_style(reply_html, style_name, config):
    """Apply style template. Returns (body_dict, is_card)."""
    if not style_name or style_name == "plain":
        return {"contentType": "html", "content": reply_html}, False

    # Try JSON (Adaptive Card) first
    json_path = STYLES_DIR / f"{style_name}.json"
    if json_path.exists():
        try:
            template = json.loads(json_path.read_text())
            plain = re.sub(r'<[^>]+>', '', reply_html).strip()
            plain = plain.replace(BOT_SIGNATURE, '').strip()
            # Check for [topic] sections
            if re.search(r'\[[^\]]+\]', plain):
                card = build_sectioned_card(template, plain)
                return card, True
            card_str = json.dumps(template)
            card_str = card_str.replace(
                '{{CONTENT}}',
                plain.replace('"', '\\"').replace('\n', '\\n')
            )
            card = json.loads(card_str)
            return card, True
        except Exception as e:
            print(f"WARNING: Card style '{style_name}' failed: {e}", file=sys.stderr)

    # Fall back to HTML template
    html_path = STYLES_DIR / f"{style_name}.html"
    if html_path.exists():
        try:
            template = html_path.read_text()
            styled = template.replace("{{CONTENT}}", reply_html)
            return {"contentType": "html", "content": styled}, False
        except Exception as e:
            print(f"WARNING: HTML style '{style_name}' failed: {e}", file=sys.stderr)

    # No style found — return unstyled
    return {"contentType": "html", "content": reply_html}, False


def send_message(client, chat_id, reply_html, style_name, chat_cfg):
    """Send message with style. Returns message ID or raises."""
    styled, is_card = apply_style(reply_html, style_name, {})

    if is_card:
        card_id = uuid.uuid4().hex[:32]
        body = {
            "body": {
                "contentType": "html",
                "content": f'<attachment id="{card_id}"></attachment><br><i>{BOT_SIGNATURE}</i> {PALM}'
            },
            "attachments": [{
                "id": card_id,
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": json.dumps(styled)
            }]
        }
    else:
        body = {"body": styled}

    resp = client.post(f"/me/chats/{chat_id}/messages", body=body)
    return resp.get("id")


def verify_sent(client, chat_id, msg_id):
    """Read back the message to verify delivery."""
    try:
        msgs = client.get(f"/me/chats/{chat_id}/messages?$top=1&$orderby=createdDateTime desc")
        latest = msgs.get("value", [{}])[0]
        latest_id = latest.get("id", "")
        has_attachment = len(latest.get("attachments", [])) > 0
        content_type = latest.get("body", {}).get("contentType", "")
        att_types = [a.get("contentType", "") for a in latest.get("attachments", [])]
        return {
            "verified": str(latest_id) == str(msg_id),
            "content_type": content_type,
            "has_attachment": has_attachment,
            "attachment_types": att_types
        }
    except Exception as e:
        return {"verified": False, "error": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Send Teams message directly via Graph API")
    parser.add_argument("--chat-id", help="Teams chat ID")
    parser.add_argument("--chat", help="Chat label from config.json")
    parser.add_argument("--style", help="Override style (island, clean, plain)")
    parser.add_argument("--no-verify", action="store_true", help="Skip delivery verification")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    args = parser.parse_args()

    # Read message from stdin
    reply = sys.stdin.read().strip()
    if not reply:
        print("ERROR: No message (stdin empty)", file=sys.stderr)
        sys.exit(1)

    config = load_config()

    # Resolve target
    target = args.chat_id or args.chat
    if not target:
        print("ERROR: Provide --chat-id or --chat", file=sys.stderr)
        sys.exit(1)

    chat_id, chat_cfg = resolve_chat(config, target)
    if not chat_id:
        print(f"ERROR: Could not resolve chat '{target}'", file=sys.stderr)
        sys.exit(1)

    chat_cfg = chat_cfg or {}
    label = chat_cfg.get("label", chat_id[:30])

    # Check access
    if chat_cfg.get("access") == "read-only":
        print(f"BLOCKED: '{label}' is read-only", file=sys.stderr)
        sys.exit(1)
    if chat_cfg.get("disabled"):
        print(f"BLOCKED: '{label}' is disabled", file=sys.stderr)
        sys.exit(1)

    # Enforce bookends + convert
    reply = enforce_bookends(reply)
    reply_html = md_to_html(reply)
    signed = f"{reply_html}<br><br><i>{BOT_SIGNATURE}</i>"

    # Determine style
    style = args.style or chat_cfg.get("style", "clean")

    # Send
    tm = TokenManager()
    token = tm.get_token()
    client = GraphClient(token)

    msg_id = send_message(client, chat_id, signed, style, chat_cfg)

    result = {
        "status": "sent",
        "chat": label,
        "chat_id": chat_id,
        "message_id": msg_id,
        "style": style,
    }

    # Verify
    if not args.no_verify:
        verification = verify_sent(client, chat_id, msg_id)
        result["verification"] = verification

    # Mark responded in tracker
    try:
        tracker_dir = str(Path.home() / ".openclaw" / "workspace" / "scripts")
        if tracker_dir not in sys.path:
            sys.path.insert(0, tracker_dir)
        from teams_tracker.tracker import TeamsTracker
        TeamsTracker().record_response(chat_id=chat_id)
        result["tracker"] = "responded"
    except Exception:
        result["tracker"] = "skipped"

    if args.json_output:
        json.dump(result, sys.stdout, indent=2)
    else:
        v = result.get("verification", {})
        verified = "✅" if v.get("verified") else "❌"
        att = f" [{', '.join(v.get('attachment_types', []))}]" if v.get("has_attachment") else ""
        print(f"{verified} Sent to '{label}' (style={style}, id={msg_id}){att}")

    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
