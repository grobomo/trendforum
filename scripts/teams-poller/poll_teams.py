#!/usr/bin/env python3
"""Teams Chat Poller for OpenClaw cron.

Polls MS Graph for new messages in a Teams chat, builds conversation context,
and outputs a formatted prompt for OpenClaw to reply to.

State is tracked in ~/.openclaw/teams-poller/state.json.
Replies are posted back via Graph API after OpenClaw responds.

Usage (standalone test):
    python3 poll_teams.py

Usage (via openclaw cron):
    Cron fires a system-event that triggers this script, reads stdout,
    and feeds it to the agent.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [teams-poller] %(message)s",
)
log = logging.getLogger(__name__)

# Add msgraph lib to path
MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient
from lib.msgraph import teams

# ── Config ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
STATE_DIR = Path.home() / ".openclaw" / "teams-poller"
STATE_FILE = STATE_DIR / "state.json"
REPLY_QUEUE_FILE = STATE_DIR / "reply_queue.json"

# How many messages to fetch for conversation context
CONTEXT_WINDOW = 30
# Max age for messages to process (seconds) — skip stale messages after outages
MAX_MESSAGE_AGE = 600  # 10 minutes
# Bot signature to detect our own posts
BOT_SIGNATURE = "--coconut-bot"


def load_config() -> dict:
    """Load config from config.json."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_state() -> dict:
    """Load poller state."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "last_processed_time": "1970-01-01T00:00:00Z",
            "processed_ids": [],
            "pending_reply": None,
        }


def save_state(state: dict):
    """Save poller state. Keep processed_ids bounded."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["processed_ids"] = state.get("processed_ids", [])[-200:]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def queue_reply(reply_info: dict):
    """Queue a reply to be sent on next poll (or immediately)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    queue = []
    try:
        with open(REPLY_QUEUE_FILE) as f:
            queue = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    queue.append(reply_info)
    # Keep bounded
    queue = queue[-20:]
    with open(REPLY_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def pop_reply_queue() -> list:
    """Pop all queued replies."""
    try:
        with open(REPLY_QUEUE_FILE) as f:
            queue = json.load(f)
        with open(REPLY_QUEUE_FILE, "w") as f:
            json.dump([], f)
        return queue
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def is_own_post(text: str) -> bool:
    """Check if a message is our own bot post."""
    return BOT_SIGNATURE in (text or "")


def parse_timestamp(ts: str) -> float:
    """Parse ISO timestamp to epoch seconds."""
    try:
        # Handle various formats Graph returns
        ts = ts.rstrip("Z")
        if "." in ts:
            dt = datetime.fromisoformat(ts + "+00:00")
        else:
            dt = datetime.fromisoformat(ts + "+00:00")
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def format_conversation_context(messages: list, new_msg_ids: set) -> str:
    """Format recent messages as conversation context.

    Messages are shown oldest-first. New (unprocessed) messages are marked.
    """
    lines = []
    lines.append("## Recent Teams Chat Context")
    lines.append("")

    for msg in messages:
        sender = msg.get("sender_name", "?")
        text = msg.get("text", "").strip()
        ts = msg.get("timestamp", "")
        msg_id = msg.get("message_id", "")
        is_bot = msg.get("is_bot", False)

        if not text:
            continue

        # Format timestamp compactly
        try:
            dt = datetime.fromisoformat(ts.rstrip("Z") + "+00:00")
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            time_str = "??:??"

        marker = " ← NEW" if msg_id in new_msg_ids else ""
        bot_tag = " [you]" if is_bot else ""
        lines.append(f"[{time_str}] {sender}{bot_tag}: {text}{marker}")

    return "\n".join(lines)


def poll():
    """Main poll function. Returns formatted context if new messages found."""
    config = load_config()
    state = load_state()

    chat_id = config.get("chat_id", "")
    if not chat_id:
        log.error("No chat_id in config.json")
        return None

    global BOT_SIGNATURE
    BOT_SIGNATURE = config.get("bot_signature", BOT_SIGNATURE)

    # Get Graph client
    try:
        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No valid Graph token")
            return None
        client = GraphClient(token=token)
    except Exception as e:
        log.error("Graph auth failed: %s", e)
        return None

    # Fetch recent messages
    try:
        raw_messages = teams.get_chat_messages(
            client, chat_id, top=CONTEXT_WINDOW,
            order_by="createdDateTime desc",
        )
    except Exception as e:
        log.error("Failed to fetch messages: %s", e)
        return None

    # Parse all messages for context
    parsed = []
    for msg in raw_messages:
        p = teams.parse_message(msg)
        p["is_bot"] = is_own_post(p.get("text", ""))
        parsed.append(p)

    # Reverse for chronological order
    parsed.reverse()

    # Find new messages
    last_time = state.get("last_processed_time", "1970-01-01T00:00:00Z")
    processed_set = set(state.get("processed_ids", []))
    now = time.time()

    new_messages = []
    for msg in parsed:
        msg_id = msg["message_id"]
        ts = msg["timestamp"]

        if ts <= last_time or msg_id in processed_set:
            continue
        if msg["is_bot"]:
            # Still mark as processed so we don't re-check
            state.setdefault("processed_ids", []).append(msg_id)
            continue
        if not msg.get("sender_name"):
            state.setdefault("processed_ids", []).append(msg_id)
            continue

        # Skip stale messages
        msg_age = now - parse_timestamp(ts)
        if msg_age > MAX_MESSAGE_AGE:
            log.info("Skipping stale message from %s (%.0fs old)", msg["sender_name"], msg_age)
            state.setdefault("processed_ids", []).append(msg_id)
            continue

        new_messages.append(msg)

    if not new_messages:
        save_state(state)
        return None

    # Build the new message IDs set for marking in context
    new_ids = {m["message_id"] for m in new_messages}

    # Build context + new messages prompt
    context = format_conversation_context(parsed, new_ids)

    # Build the prompt for OpenClaw
    parts = []
    parts.append(context)
    parts.append("")
    parts.append("---")
    parts.append("")

    if len(new_messages) == 1:
        msg = new_messages[0]
        parts.append(f"New Teams message from **{msg['sender_name']}**:")
        parts.append(msg["text"])
    else:
        parts.append(f"{len(new_messages)} new Teams messages:")
        for msg in new_messages:
            parts.append(f"- **{msg['sender_name']}**: {msg['text']}")

    parts.append("")
    parts.append("Reply to the new message(s). Your reply will be posted to the Teams chat.")
    parts.append("If the messages don't need a reply (casual banter, already answered, etc.), respond with just: TEAMS_NO_REPLY")

    prompt = "\n".join(parts)

    # Update state — mark all new as processed
    for msg in new_messages:
        state.setdefault("processed_ids", []).append(msg["message_id"])

    # Track the latest timestamp
    all_timestamps = [m["timestamp"] for m in parsed if m["timestamp"]]
    if all_timestamps:
        state["last_processed_time"] = max(all_timestamps)

    # Store who we need to reply to (for the reply-posting step)
    state["pending_reply"] = {
        "chat_id": chat_id,
        "senders": [
            {"name": m["sender_name"], "id": m.get("sender_id", "")}
            for m in new_messages
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    save_state(state)
    return prompt


def send_reply(reply_text: str):
    """Post a reply back to the Teams chat."""
    config = load_config()
    state = load_state()

    chat_id = config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)
    pending = state.get("pending_reply")

    if not chat_id or not pending:
        log.warning("No pending reply or chat_id")
        return False

    try:
        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No token for reply")
            return False
        client = GraphClient(token=token)
    except Exception as e:
        log.error("Auth failed for reply: %s", e)
        return False

    # Build reply with mentions and signature
    senders = pending.get("senders", [])
    signed = f"{reply_text}\n\n<i>{bot_signature}</i>"

    mentions = []
    mention_html_parts = []
    for i, sender in enumerate(senders):
        if sender.get("id"):
            mention_html_parts.append(f'<at id="{i}">{sender["name"]}</at>')
            mentions.append({
                "id": i,
                "mentionText": sender["name"],
                "mentioned": {
                    "user": {
                        "id": sender["id"],
                        "displayName": sender["name"],
                        "userIdentityType": "aadUser",
                    }
                },
            })

    if mention_html_parts:
        body_html = " ".join(mention_html_parts) + " " + signed
    else:
        body_html = signed

    try:
        teams.send_chat_message(client, chat_id, body_html, mentions=mentions)
        log.info("Posted reply to Teams chat")
        state["pending_reply"] = None
        save_state(state)
        return True
    except Exception as e:
        log.error("Failed to post reply: %s", e)
        return False


if __name__ == "__main__":
    result = poll()
    if result:
        print(result)
        sys.exit(0)
    else:
        log.info("No new messages")
        sys.exit(0)
