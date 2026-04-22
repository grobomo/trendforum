#!/usr/bin/env python3
"""Teams Chat Service — fast-polling daemon for OpenClaw.

Polls MS Graph every few seconds for new messages, writes them to a
queue file that the OpenClaw cron job picks up. Replies are written
back by the cron job and this service posts them.

This runs as a systemd user service for reliability.

Usage:
    python3 teams_service.py              # Run daemon (default 5s poll)
    python3 teams_service.py --interval 3 # 3-second poll interval
    python3 teams_service.py --once       # Single poll (for testing)
"""

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [teams-service] %(message)s",
)
log = logging.getLogger(__name__)

# Add script dir for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from poll_teams import (
    load_config, load_state, save_state, parse_timestamp,
    format_conversation_context, is_own_post, BOT_SIGNATURE,
    CONTEXT_WINDOW, MAX_MESSAGE_AGE,
)
# Central tracker — shared by webhook, poller, manual Graph, and queue_reply
TRACKER_DIR = Path(__file__).parent.parent / "teams_tracker"
if str(TRACKER_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TRACKER_DIR.parent))

from teams_tracker.tracker import TeamsTracker
_tracker = TeamsTracker()

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient
from lib.msgraph import teams

# ── OpenClaw wake ────────────────────────────────────────────────

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
OPENCLAW_PORT = 18789
_gateway_token = None
_last_wake_time = 0
WAKE_DEBOUNCE_SECONDS = 10  # Don't wake more than once per 10 seconds


def _get_gateway_token() -> str | None:
    """Read gateway auth token from openclaw.json (cached)."""
    global _gateway_token
    if _gateway_token:
        return _gateway_token
    try:
        with open(OPENCLAW_CONFIG) as f:
            cfg = json.load(f)
        _gateway_token = cfg.get("gateway", {}).get("auth", {}).get("token")
        return _gateway_token
    except Exception:
        return None


def _wake_openclaw():
    """Wake OpenClaw by sending a message via the chat completions API (fire-and-forget)."""
    global _last_wake_time
    now = time.time()
    if now - _last_wake_time < WAKE_DEBOUNCE_SECONDS:
        log.debug("Wake debounced (%.0fs since last)", now - _last_wake_time)
        return
    _last_wake_time = now
    token = _get_gateway_token()
    if not token:
        log.warning("No gateway token found, skipping wake")
        return

    def _do_wake():
        try:
            payload = json.dumps({
                "model": "openclaw/main",
                "messages": [{"role": "system", "content": "New Teams message received via webhook. Run python3 /home/ubu/.openclaw/workspace/scripts/teams_tracker/check_gaps.py --minutes 1 --enriched and handle output: if TEAMS_GAPS_FOUND, compose and send replies for read-write chats via queue_reply.py, then mark responded with tracker.py respond --chat-id <id>. For read-only chats, flag important items to Joel via Slack DM. If no output, do nothing."}, {"role": "user", "content": "A new Teams message just arrived. Process it now."}],
                "stream": False,
            })
            # Fire-and-forget via curl subprocess so we don't block the poll loop
            subprocess.run(
                ["curl", "-s", "-X", "POST",
                 f"http://127.0.0.1:{OPENCLAW_PORT}/v1/chat/completions",
                 "-H", f"Authorization: Bearer {token}",
                 "-H", "Content-Type: application/json",
                 "-d", payload,
                 "--max-time", "120"],
                capture_output=True, timeout=130,
            )
            log.info("OpenClaw wake completed")
        except Exception as e:
            log.warning("Failed to wake OpenClaw: %s", e)

    # Run in background thread so poll loop isn't blocked
    t = threading.Thread(target=_do_wake, daemon=True)
    t.start()
    log.info("Sent wake to OpenClaw (background thread)")


# ── Queue files ──────────────────────────────────────────────────

QUEUE_DIR = Path.home() / ".openclaw" / "teams-poller"
INBOUND_QUEUE = QUEUE_DIR / "inbound_queue.json"
OUTBOUND_QUEUE = QUEUE_DIR / "outbound_queue.json"
PID_FILE = QUEUE_DIR / "service.pid"


def write_inbound(prompt: str, pending_reply: dict):
    """Write a new message prompt for the cron job to pick up."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "prompt": prompt,
        "pending_reply": pending_reply,
        "chat_id": pending_reply.get("chat_id", "") if pending_reply else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Atomic-ish write
    with open(INBOUND_QUEUE, "w") as f:
        json.dump(entry, f, indent=2)
    log.info("Queued inbound message for cron pickup")

    # Immediately wake OpenClaw to process the message
    _wake_openclaw()


def read_and_clear_inbound() -> dict | None:
    """Read and clear the inbound queue. Called by cron."""
    try:
        with open(INBOUND_QUEUE) as f:
            entry = json.load(f)
        # Clear it
        with open(INBOUND_QUEUE, "w") as f:
            json.dump(None, f)
        return entry
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_outbound(reply_text: str):
    """Write a reply for the service to post. Called by cron."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "reply": reply_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(OUTBOUND_QUEUE, "w") as f:
        json.dump(entry, f, indent=2)


def read_and_clear_outbound() -> list[dict]:
    """Read and clear the outbound queue. Returns list of reply entries."""
    try:
        with open(OUTBOUND_QUEUE) as f:
            data = json.load(f)
        entries = []
        if isinstance(data, list):
            entries = [e for e in data if isinstance(e, dict) and e.get("reply")]
        elif isinstance(data, dict) and data.get("reply"):
            entries = [data]  # legacy single-object
        if entries:
            with open(OUTBOUND_QUEUE, "w") as f:
                json.dump([], f)
            return entries
        return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ── Service ──────────────────────────────────────────────────────

_shutdown = False


def _get_chat_config(config: dict, chat_id: str) -> dict | None:
    """Look up per-chat config from the chats[] array."""
    for c in config.get("chats", []):
        if c.get("id") == chat_id:
            return c
    return None


def _track_record(chat_id: str, msg_id: str, sender: str, text: str = "", label: str = ""):
    """Record a human message in the central tracker."""
    try:
        _tracker.record_message(
            chat_id=chat_id, msg_id=msg_id, sender=sender,
            text=text, source="poller", label=label,
        )
    except Exception as e:
        log.warning("Failed to record in tracker: %s", e)


def _track_respond(chat_id: str):
    """Mark all pending messages in a chat as responded."""
    try:
        _tracker.record_response(chat_id=chat_id)
    except Exception as e:
        log.warning("Failed to mark responded in tracker: %s", e)


def poll_once(client: GraphClient, config: dict, state: dict, chat_id: str = None) -> str | None:
    """Single poll cycle for one chat. Returns prompt text if new messages found."""
    chat_id = chat_id or config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)
    chat_cfg = _get_chat_config(config, chat_id)
    chat_label = chat_cfg.get("label", "unknown") if chat_cfg else "unknown"
    access = chat_cfg.get("access", "read-write") if chat_cfg else "read-write"

    # Skip disabled chats entirely — don't poll, don't queue
    if access == "disabled":
        return None

    try:
        raw_messages = teams.get_chat_messages(
            client, chat_id, top=CONTEXT_WINDOW,
            order_by="createdDateTime desc",
        )
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "expired" in err_str.lower():
            log.error("Auth expired: %s", e)
            raise  # Bubble up to trigger re-auth in main loop
        log.error("Failed to fetch messages: %s", e)
        return None

    # Parse all messages
    parsed = []
    for msg in raw_messages:
        p = teams.parse_message(msg)
        p["is_bot"] = is_own_post(p.get("text", ""))
        parsed.append(p)
    parsed.reverse()

    # Find new messages
    # Use per-chat state keys so chats don't interfere with each other
    per_chat_key = f"chat:{chat_id}"
    chat_state = state.get(per_chat_key, {})
    last_time = chat_state.get("last_processed_time", state.get("last_processed_time", "1970-01-01T00:00:00Z"))
    processed_set = set(state.get("processed_ids", []))
    now = time.time()

    new_messages = []
    for msg in parsed:
        msg_id = msg["message_id"]
        ts = msg["timestamp"]

        if ts <= last_time or msg_id in processed_set:
            continue
        if msg["is_bot"]:
            state.setdefault("processed_ids", []).append(msg_id)
            continue
        if not msg.get("sender_name"):
            state.setdefault("processed_ids", []).append(msg_id)
            continue

        msg_age = now - parse_timestamp(ts)
        if msg_age > MAX_MESSAGE_AGE:
            log.info("Skipping stale message from %s (%.0fs old)", msg["sender_name"], msg_age)
            state.setdefault("processed_ids", []).append(msg_id)
            continue

        new_messages.append(msg)

    # Track ALL new human messages in the central tracker
    for msg in new_messages:
        _track_record(chat_id, msg["message_id"], msg["sender_name"],
                       text=msg.get("text", ""), label=chat_label)

    if not new_messages:
        return None

    new_ids = {m["message_id"] for m in new_messages}
    context = format_conversation_context(parsed, new_ids)

    parts = [context, "", "---", ""]
    if len(new_messages) == 1:
        msg = new_messages[0]
        parts.append(f"New Teams message from **{msg['sender_name']}**:")
        parts.append(msg["text"])
    else:
        parts.append(f"{len(new_messages)} new Teams messages:")
        for msg in new_messages:
            parts.append(f"- **{msg['sender_name']}**: {msg['text']}")

    # Tag which chat and access mode this is from
    parts.append("")
    parts.append(f"[Chat: {chat_label} | Access: {access}]")

    if access == "read-only":
        note = chat_cfg.get("note", "")
        parts.append(f"⚠️ READ-ONLY CHAT — Do NOT reply to this chat. {note}")
        parts.append("Summarize or flag anything important to Joel via Slack DM instead.")
        parts.append("Respond with: TEAMS_NO_REPLY")
    else:
        parts.append("Reply to the new message(s). Your reply will be posted to the Teams chat.")
        parts.append("If the messages don't need a reply (casual banter, already answered, etc.), respond with just: TEAMS_NO_REPLY")

    prompt = "\n".join(parts)

    # Update state
    for msg in new_messages:
        state.setdefault("processed_ids", []).append(msg["message_id"])

    all_timestamps = [m["timestamp"] for m in parsed if m["timestamp"]]
    if all_timestamps:
        chat_state["last_processed_time"] = max(all_timestamps)
        state[per_chat_key] = chat_state

    state["pending_reply"] = {
        "chat_id": chat_id,
        "chat_label": chat_label,
        "access": access,
        "senders": [
            {"name": m["sender_name"], "id": m.get("sender_id", "")}
            for m in new_messages
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    save_state(state)
    return prompt


def md_to_html(text):
    """Convert common markdown to Teams-compatible HTML."""
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    for line in lines:
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
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', line)
        line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
        if re.match(r'^\s*[•\-]\s+', line):
            line = re.sub(r'^\s*[•\-]\s+', '• ', line)
        if line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(line)
    if in_code_block:
        html_lines.append('</pre>')
    return '<br>'.join(html_lines)


def verify_message(client: GraphClient, chat_id: str, message_id: str,
                   max_retries: int = 2, delay: float = 2.0) -> dict:
    """Verify a sent message via Graph API GET.

    Returns dict with:
      verified: bool
      sender: str (who Graph says sent it — catches delegated-auth issues)
      body_preview: str
      attempts: int
    Core principle: never trust your own logs — always verify via live data.
    """
    import time as _time
    result_info = {"verified": False, "sender": "", "body_preview": "", "attempts": 0}
    for attempt in range(max_retries):
        _time.sleep(delay)
        result_info["attempts"] = attempt + 1
        try:
            result = client.get(f'/me/chats/{chat_id}/messages/{message_id}')
            if result and result.get('id'):
                result_info["verified"] = True
                result_info["sender"] = (
                    result.get('from', {}).get('user', {}).get('displayName', '?')
                )
                body = result.get('body', {}).get('content', '')
                # Strip HTML for preview
                import re as _re
                result_info["body_preview"] = _re.sub(r'<[^>]+>', '', body)[:80]
                return result_info
        except Exception as e:
            log.warning("Verify attempt %d failed for msg %s: %s",
                        attempt + 1, message_id, e)
    return result_info


def post_reply(client: GraphClient, config: dict, reply_text: str, target_chat_id: str = None):
    """Post a reply to Teams with live verification.
    
    Blocks posting to read-only chats. After sending, verifies the message
    actually exists via Graph API GET. Logs VERIFIED or VERIFY_FAILED.
    """
    chat_id = target_chat_id or config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)

    # SAFETY: check access policy before posting
    chat_cfg = _get_chat_config(config, chat_id)
    if chat_cfg and chat_cfg.get("access") == "read-only":
        log.warning("BLOCKED: attempted post to read-only chat '%s' (%s)",
                    chat_cfg.get("label", "?"), chat_id[:30])
        return

    # Enforce 🌴 bookends (SOUL.md contract) — second safety net after queue_reply.py
    PALM = "\U0001f334"  # 🌴
    if not reply_text.startswith(PALM):
        reply_text = f"{PALM} {reply_text}"
    if not reply_text.rstrip().endswith(PALM):
        reply_text = f"{reply_text.rstrip()} {PALM}"

    reply_html = md_to_html(reply_text)
    signed = f"{reply_html}<br><br><i>{bot_signature}</i>"

    chat_label = chat_cfg.get("label", "?") if chat_cfg else "?"

    # Apply per-chat style template if configured
    style_name = chat_cfg.get("style", "") if chat_cfg else ""
    use_adaptive_card = False
    adaptive_card_json = None
    if style_name and style_name != "plain":
        # Prefer .json (Adaptive Card) over .html
        json_style_path = Path(__file__).parent / "styles" / f"{style_name}.json"
        html_style_path = Path(__file__).parent / "styles" / f"{style_name}.html"
        if json_style_path.exists():
            try:
                import copy
                template = json.loads(json_style_path.read_text())
                # Strip HTML tags from reply for Adaptive Card plain text
                import re as _re
                plain_content = _re.sub(r'<[^>]+>', '', reply_text)
                # Remove bot signature from content (card has its own)
                plain_content = plain_content.replace(bot_signature, '').strip()
                # Walk the card body and replace {{CONTENT}} placeholders
                card_str = json.dumps(template)
                card_str = card_str.replace('{{CONTENT}}', plain_content.replace('"', '\\"').replace('\n', '\\n'))
                adaptive_card_json = json.loads(card_str)
                use_adaptive_card = True
                log.info("Applied Adaptive Card style '%s' to message for %s", style_name, chat_label)
            except Exception as e:
                log.warning("Failed to apply card style '%s': %s — falling back to unstyled", style_name, e)
        elif html_style_path.exists():
            try:
                template = html_style_path.read_text()
                signed = template.replace("{{CONTENT}}", signed)
                log.info("Applied HTML style '%s' to message for %s", style_name, chat_label)
            except Exception as e:
                log.warning("Failed to apply style '%s': %s — sending unstyled", style_name, e)
    # Check config for verify toggle
    do_verify = config.get("verify_sends", True)

    try:
        if use_adaptive_card and adaptive_card_json:
            # Send as Adaptive Card attachment
            import uuid
            card_id = str(uuid.uuid4()).replace('-', '')[:32]
            # Footer only outside card — plain text area for easy reaction long-tap
            footer = f"<i>{bot_signature}</i> \U0001f334"
            payload = {
                "body": {
                    "contentType": "html",
                    "content": f'<attachment id="{card_id}"></attachment><br>{footer}',
                },
                "attachments": [
                    {
                        "id": card_id,
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": json.dumps(adaptive_card_json),
                        "name": f"Coconut ({style_name})",
                    }
                ],
            }
            result = client.post(f"/me/chats/{chat_id}/messages", body=payload)
        else:
            result = teams.send_chat_message(client, chat_id, signed)
        msg_id = result.get('id', '') if isinstance(result, dict) else ''
        post_sender = ''
        if isinstance(result, dict):
            post_sender = result.get('from', {}).get('user', {}).get('displayName', '')

        # Track our response in the central tracker
        _track_respond(chat_id)

        if msg_id and do_verify:
            # Live verification — core principle: trust live data, not logs
            vinfo = verify_message(client, chat_id, msg_id)
            if vinfo["verified"]:
                log.info("VERIFIED: Reply in %s msg=%s graph_sender=%s attempts=%d",
                         chat_label, msg_id, vinfo["sender"], vinfo["attempts"])
                # Flag if sender mismatch (delegated auth showing as Joel)
                if vinfo["sender"] and "coconut" not in vinfo["sender"].lower() \
                        and "bot" not in vinfo["sender"].lower():
                    log.warning("SENDER_MISMATCH: Message shows as '%s' not bot — "
                                "delegated auth issue", vinfo["sender"])
            else:
                log.error("VERIFY_FAILED: 201 returned but msg %s not found in %s after %d attempts",
                          msg_id, chat_label, vinfo["attempts"])
        elif msg_id:
            log.info("Posted reply to %s msg=%s (verify_sends=off)", chat_label, msg_id)
        else:
            log.warning("POST returned no message ID for %s — cannot verify",
                        chat_label)
    except Exception as e:
        log.error("Failed to post reply to %s: %s", chat_label, e)


def run_service(interval: int = 5):
    """Main service loop."""
    global _shutdown

    config = load_config()
    chat_configs = config.get("chats", [])
    if not chat_configs:
        # Legacy fallback
        chat_id = config.get("chat_id", "")
        if not chat_id:
            log.error("No chats[] or chat_id in config.json")
            sys.exit(1)
        chat_configs = [{"id": chat_id, "label": "default", "access": "read-write"}]
    log.info("Monitoring %d chat(s): %s", len(chat_configs),
             ", ".join(f"{c.get('label','?')} ({c.get('access','rw')})" for c in chat_configs))

    # Write PID file
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    # Signal handling
    def handle_signal(signum, frame):
        global _shutdown
        _shutdown = True
        log.info("Shutdown signal received")

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info("Teams service starting (poll every %ds)", interval)

    # Auth
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.error("No valid Graph token")
        sys.exit(1)
    client = GraphClient(token=token)

    token_refresh_time = time.time()
    state = load_state()
    consecutive_errors = 0

    while not _shutdown:
        try:
            # Refresh token every 15 minutes (tokens can expire in <30m)
            if time.time() - token_refresh_time > 900:
                token = tm.get_token()
                if token:
                    client = GraphClient(token=token)
                    token_refresh_time = time.time()
                    log.info("Token refreshed")

            # Poll all configured chats
            chat_configs = config.get("chats", [])
            if not chat_configs:
                # Legacy fallback: single chat_id
                chat_configs = [{"id": config.get("chat_id", ""), "label": "default", "access": "read-write"}]

            for chat_cfg in chat_configs:
                cid = chat_cfg.get("id", "")
                if not cid:
                    continue
                prompt = poll_once(client, config, state, chat_id=cid)
                if prompt:
                    write_inbound(prompt, state.get("pending_reply"))

            # Check for outbound replies to post (array-based)
            outbound_entries = read_and_clear_outbound()
            for outbound in outbound_entries:
                reply = outbound.get("reply", "").strip()
                if reply and reply != "TEAMS_NO_REPLY":
                    target = outbound.get("chat_id") or config.get("chat_id", "")
                    post_reply(client, config, reply, target_chat_id=target)

            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            log.error("Poll error (streak=%d): %s", consecutive_errors, e)
            if consecutive_errors >= 3:
                # Force refresh on errors — don't use cached token
                try:
                    tm._tokens = None  # Clear cached token to force re-read
                    token = tm.get_token()
                    if token:
                        client = GraphClient(token=token)
                        token_refresh_time = time.time()
                        log.info("Re-authenticated after error streak")
                        consecutive_errors = 0
                    else:
                        log.error("Token refresh returned None — refresh token may be dead")
                except Exception as re_err:
                    log.error("Re-auth failed: %s", re_err)

        # Sleep in small increments for responsive shutdown
        for _ in range(interval * 2):
            if _shutdown:
                break
            time.sleep(0.5)

    # Cleanup
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    log.info("Teams service stopped")


def main():
    parser = argparse.ArgumentParser(description="Teams Chat Service")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    parser.add_argument("--once", action="store_true", help="Single poll cycle")
    args = parser.parse_args()

    if args.once:
        config = load_config()
        state = load_state()
        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No token")
            sys.exit(1)
        client = GraphClient(token=token)
        prompt = poll_once(client, config, state)
        if prompt:
            print(prompt)
        else:
            log.info("No new messages")
    else:
        run_service(args.interval)


if __name__ == "__main__":
    main()
