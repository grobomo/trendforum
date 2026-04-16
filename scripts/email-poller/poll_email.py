#!/usr/bin/env python3
"""Email Poller for OpenClaw cron.

Polls MS Graph for new unread emails, formats them as a summary
for OpenClaw to review and optionally act on.

State tracked in ~/.openclaw/email-poller/state.json.

Usage:
    python3 poll_email.py
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [email-poller] %(message)s",
)
log = logging.getLogger(__name__)

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient

# ── Config ───────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
STATE_DIR = Path.home() / ".openclaw" / "email-poller"
STATE_FILE = STATE_DIR / "state.json"

# Max emails per poll
MAX_EMAILS = 10
# Max body length per email
MAX_BODY_LENGTH = 2000


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_check": "1970-01-01T00:00:00Z", "processed_ids": []}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["processed_ids"] = state.get("processed_ids", [])[-200:]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def strip_html(html: str) -> str:
    """Basic HTML to text conversion."""
    import re
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</?(div|p|tr|li|blockquote|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def poll() -> str | None:
    """Poll for new unread emails. Returns formatted summary if any found."""
    config = load_config()
    state = load_state()

    # Auth
    try:
        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No valid Graph token")
            return None
        client = GraphClient(token=token)
    except Exception as e:
        log.error("Auth failed: %s", e)
        return None

    # Fetch unread emails
    try:
        params = {
            "$filter": "isRead eq false",
            "$orderby": "receivedDateTime desc",
            "$top": str(MAX_EMAILS),
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,importance,hasAttachments,flag",
        }

        # If we have a last check time, also filter by date to reduce volume
        last_check = state.get("last_check", "1970-01-01T00:00:00Z")
        if last_check and last_check != "1970-01-01T00:00:00Z":
            params["$filter"] = f"isRead eq false and receivedDateTime ge {last_check}"

        result = client.get("/me/messages", params=params)
        emails = result.get("value", [])
    except Exception as e:
        log.error("Failed to fetch emails: %s", e)
        return None

    processed_set = set(state.get("processed_ids", []))

    new_emails = []
    for email in emails:
        eid = email.get("id", "")
        if eid in processed_set:
            continue
        new_emails.append(email)
        state.setdefault("processed_ids", []).append(eid)

    if not new_emails:
        # Update last_check even if no new emails
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return None

    # Format email summary
    parts = []
    parts.append(f"## 📧 {len(new_emails)} New Email(s)\n")

    for email in new_emails:
        sender = email.get("from", {}).get("emailAddress", {})
        sender_name = sender.get("name", "Unknown")
        sender_email = sender.get("address", "")
        subject = email.get("subject", "(no subject)")
        received = email.get("receivedDateTime", "")
        importance = email.get("importance", "normal")
        has_attachments = email.get("hasAttachments", False)
        flagged = email.get("flag", {}).get("flagStatus", "") == "flagged"

        # Get body text
        body = email.get("body", {})
        if body.get("contentType") == "html":
            body_text = strip_html(body.get("content", ""))
        else:
            body_text = body.get("content", "")

        body_text = body_text[:MAX_BODY_LENGTH]
        if len(body_text) == MAX_BODY_LENGTH:
            body_text += "\n[... truncated]"

        # Format timestamp
        try:
            dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, TypeError):
            time_str = received

        tags = []
        if importance == "high":
            tags.append("⚠️ HIGH PRIORITY")
        if has_attachments:
            tags.append("📎 attachments")
        if flagged:
            tags.append("🚩 flagged")
        tag_str = f" [{', '.join(tags)}]" if tags else ""

        parts.append(f"### From: {sender_name} <{sender_email}>{tag_str}")
        parts.append(f"**Subject:** {subject}")
        parts.append(f"**Received:** {time_str}")
        parts.append(f"\n{body_text}")
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("Review these emails. For each one, briefly note:")
    parts.append("- Whether it needs attention or can be ignored")
    parts.append("- If urgent, flag it for Joel")
    parts.append("- Summary of key points")
    parts.append("")
    parts.append("If nothing needs attention, respond with just: EMAIL_NO_ACTION")

    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return "\n".join(parts)


if __name__ == "__main__":
    result = poll()
    if result:
        print(result)
    else:
        log.info("No new emails")
