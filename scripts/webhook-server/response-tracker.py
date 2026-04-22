#!/usr/bin/env python3
"""
Teams Response Tracker — tracks which messages need responses and which have been answered.

Works with both webhooks (primary) and poller (fallback).
Persists state to disk so it survives context resets and session compactions.

Usage:
    python3 response-tracker.py record --chat-id <id> --msg-id <id> --sender <name>
    python3 response-tracker.py respond --chat-id <id> --msg-id <id>
    python3 response-tracker.py pending              # Show all unanswered messages
    python3 response-tracker.py stale [--minutes 15]  # Show messages waiting > N minutes
    python3 response-tracker.py status               # Overview of all chats
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path.home() / ".openclaw" / "workspace" / "scripts" / "webhook-server" / "state" / "response-tracker.json"
CONFIG_FILE = Path.home() / ".openclaw" / "workspace" / "scripts" / "teams-poller" / "config.json"

# Bot user IDs / display names to ignore (don't track bot messages as needing response)
BOT_INDICATORS = ["coconut-bot", "--coconut-bot", "[you]", "🦎 Molty"]


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"messages": {}, "responded": {}, "stats": {"total_recorded": 0, "total_responded": 0}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_chat_name(chat_id, config):
    """Look up chat name from config."""
    for chat in config.get("chats", []):
        if chat.get("id") == chat_id:
            return chat.get("alias") or chat.get("name") or chat_id[:20]
    return chat_id[:20]


def is_bot_message(sender):
    """Check if sender is a bot."""
    if not sender:
        return True
    for indicator in BOT_INDICATORS:
        if indicator.lower() in sender.lower():
            return True
    return False


def cmd_record(args):
    """Record a new message that needs a response."""
    if is_bot_message(args.sender):
        return  # Don't track bot messages

    state = load_state()
    key = f"{args.chat_id}:{args.msg_id}"

    if key in state["messages"]:
        return  # Already tracked

    state["messages"][key] = {
        "chat_id": args.chat_id,
        "msg_id": args.msg_id,
        "sender": args.sender,
        "timestamp": time.time(),
        "source": args.source or "webhook",
    }
    state["stats"]["total_recorded"] += 1
    save_state(state)
    print(f"📥 Recorded: {args.sender} in {args.chat_id[:20]}... (msg {args.msg_id})")


def cmd_respond(args):
    """Mark a message (or all pending in a chat) as responded."""
    state = load_state()

    if args.msg_id:
        # Mark specific message
        key = f"{args.chat_id}:{args.msg_id}"
        if key in state["messages"]:
            msg = state["messages"].pop(key)
            state["responded"][key] = {
                **msg,
                "responded_at": time.time(),
                "response_time_s": time.time() - msg["timestamp"],
            }
            state["stats"]["total_responded"] += 1
    else:
        # Mark all pending in this chat as responded
        to_move = [k for k, v in state["messages"].items() if v["chat_id"] == args.chat_id]
        for key in to_move:
            msg = state["messages"].pop(key)
            state["responded"][key] = {
                **msg,
                "responded_at": time.time(),
                "response_time_s": time.time() - msg["timestamp"],
            }
            state["stats"]["total_responded"] += 1

    # Prune responded older than 24h to keep file small
    cutoff = time.time() - 86400
    state["responded"] = {k: v for k, v in state["responded"].items() if v.get("responded_at", 0) > cutoff}

    save_state(state)
    print(f"✅ Marked responded: {args.chat_id[:20]}...")


def cmd_pending(args):
    """Show all messages waiting for response."""
    state = load_state()
    config = load_config()
    pending = state.get("messages", {})

    if not pending:
        print("No pending messages.")
        return

    # Group by chat
    by_chat = {}
    for key, msg in pending.items():
        cid = msg["chat_id"]
        if cid not in by_chat:
            by_chat[cid] = []
        by_chat[cid].append(msg)

    for chat_id, msgs in by_chat.items():
        name = get_chat_name(chat_id, config)
        print(f"\n📬 {name} ({len(msgs)} pending):")
        for msg in sorted(msgs, key=lambda m: m["timestamp"]):
            age_min = (time.time() - msg["timestamp"]) / 60
            print(f"  • {msg['sender']} ({age_min:.0f}m ago) [msg:{msg['msg_id'][:10]}] via {msg.get('source', '?')}")


def cmd_stale(args):
    """Show messages waiting longer than threshold."""
    state = load_state()
    config = load_config()
    threshold = args.minutes * 60
    now = time.time()

    stale = {k: v for k, v in state.get("messages", {}).items() if now - v["timestamp"] > threshold}

    if not stale:
        print(f"No messages older than {args.minutes} minutes.")
        return

    print(f"⚠️ {len(stale)} stale message(s) (>{args.minutes}m):")
    for key, msg in sorted(stale.items(), key=lambda x: x[1]["timestamp"]):
        name = get_chat_name(msg["chat_id"], config)
        age_min = (now - msg["timestamp"]) / 60
        print(f"  🔴 {name}: {msg['sender']} ({age_min:.0f}m ago)")


def cmd_status(args):
    """Overview of response tracking state."""
    state = load_state()
    config = load_config()
    pending = state.get("messages", {})
    responded = state.get("responded", {})
    stats = state.get("stats", {})

    print("📊 Response Tracker Status")
    print(f"  Pending: {len(pending)}")
    print(f"  Responded (24h): {len(responded)}")
    print(f"  Total recorded: {stats.get('total_recorded', 0)}")
    print(f"  Total responded: {stats.get('total_responded', 0)}")

    if responded:
        times = [v.get("response_time_s", 0) for v in responded.values() if v.get("response_time_s")]
        if times:
            avg = sum(times) / len(times)
            print(f"  Avg response time: {avg / 60:.1f}m")

    if pending:
        print("\n  Pending by chat:")
        by_chat = {}
        for msg in pending.values():
            cid = msg["chat_id"]
            by_chat[cid] = by_chat.get(cid, 0) + 1
        for cid, count in by_chat.items():
            name = get_chat_name(cid, config)
            print(f"    {name}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Teams Response Tracker")
    sub = parser.add_subparsers(dest="command")

    p_record = sub.add_parser("record")
    p_record.add_argument("--chat-id", required=True)
    p_record.add_argument("--msg-id", required=True)
    p_record.add_argument("--sender", required=True)
    p_record.add_argument("--source", default="webhook")

    p_respond = sub.add_parser("respond")
    p_respond.add_argument("--chat-id", required=True)
    p_respond.add_argument("--msg-id", default=None)

    p_pending = sub.add_parser("pending")

    p_stale = sub.add_parser("stale")
    p_stale.add_argument("--minutes", type=int, default=15)

    p_status = sub.add_parser("status")

    args = parser.parse_args()

    if args.command == "record":
        cmd_record(args)
    elif args.command == "respond":
        cmd_respond(args)
    elif args.command == "pending":
        cmd_pending(args)
    elif args.command == "stale":
        cmd_stale(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
