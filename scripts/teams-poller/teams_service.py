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
                "messages": [{"role": "system", "content": "New Teams message received. Run python3 /home/ubu/.openclaw/workspace/scripts/poll_all.py and handle output: TEAMS = compose reply then run python3 /home/ubu/.openclaw/workspace/scripts/teams-poller/queue_reply.py with your reply. GITHUB = compose replies in GITHUB_REPLY format then run python3 /home/ubu/.openclaw/workspace/scripts/github-poller/send_reply.py. EMAIL = summarize and flag urgent items. If no output, do nothing."}, {"role": "user", "content": "A new Teams message just arrived. Process it now."}],
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


def read_and_clear_outbound() -> dict | None:
    """Read and clear the outbound queue."""
    try:
        with open(OUTBOUND_QUEUE) as f:
            entry = json.load(f)
        if entry and entry.get("reply"):
            with open(OUTBOUND_QUEUE, "w") as f:
                json.dump(None, f)
            return entry
        return None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ── Service ──────────────────────────────────────────────────────

_shutdown = False


def _get_chat_config(config: dict, chat_id: str) -> dict | None:
    """Look up per-chat config from the chats[] array."""
    for c in config.get("chats", []):
        if c.get("id") == chat_id:
            return c
    return None


def poll_once(client: GraphClient, config: dict, state: dict, chat_id: str = None) -> str | None:
    """Single poll cycle for one chat. Returns prompt text if new messages found."""
    chat_id = chat_id or config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)
    chat_cfg = _get_chat_config(config, chat_id)
    chat_label = chat_cfg.get("label", "unknown") if chat_cfg else "unknown"
    access = chat_cfg.get("access", "read-write") if chat_cfg else "read-write"

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


def post_reply(client: GraphClient, config: dict, reply_text: str, target_chat_id: str = None):
    """Post a reply to Teams. Blocks posting to read-only chats."""
    chat_id = target_chat_id or config.get("chat_id", "")
    bot_signature = config.get("bot_signature", BOT_SIGNATURE)

    # SAFETY: check access policy before posting
    chat_cfg = _get_chat_config(config, chat_id)
    if chat_cfg and chat_cfg.get("access") == "read-only":
        log.warning("BLOCKED: attempted post to read-only chat '%s' (%s)",
                    chat_cfg.get("label", "?"), chat_id[:30])
        return

    signed = f"{reply_text}\n\n<i>{bot_signature}</i>"
    try:
        teams.send_chat_message(client, chat_id, signed)
        log.info("Posted reply to Teams chat %s (%s)", 
                 chat_cfg.get("label", "?") if chat_cfg else "?", chat_id[:30])
    except Exception as e:
        log.error("Failed to post reply: %s", e)


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

            # Check for outbound replies to post
            outbound = read_and_clear_outbound()
            if outbound and outbound.get("reply"):
                reply = outbound["reply"].strip()
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
