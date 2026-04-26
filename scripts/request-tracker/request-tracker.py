#!/usr/bin/env python3
"""
Cross-Channel Request/Response Tracker
=======================================
Tracks where requests originate (Slack, Teams, Trello cron, etc.) and ensures
responses are delivered back to the originating channel.

MVP Scope:
  - Record a request with its source channel + context
  - Match outgoing responses to open requests
  - List pending/undelivered requests
  - Suggest delivery targets for responses
  - Auto-expire old entries

Usage:
    python3 request-tracker.py record --channel teams --chat-id <id> --topic "research X" [--sender <name>]
    python3 request-tracker.py match --topic "research X"   # Find where this topic was requested
    python3 request-tracker.py deliver --request-id <id>    # Mark a request as delivered
    python3 request-tracker.py pending                      # Show all undelivered requests
    python3 request-tracker.py status                       # Overview stats
    python3 request-tracker.py cleanup [--hours 72]         # Expire old entries
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state" / "request-tracker.json"

# Supported channels
CHANNELS = {
    "slack": {"name": "Slack", "prefix": "slack"},
    "teams": {"name": "Teams", "prefix": "teams"},
    "trello": {"name": "Trello", "prefix": "trello"},
    "github": {"name": "GitHub", "prefix": "github"},
    "email": {"name": "Email", "prefix": "email"},
    "cron": {"name": "Cron/System", "prefix": "cron"},
}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "requests": {},  # request_id -> request object
            "delivered": {},  # request_id -> delivery info
            "stats": {
                "total_recorded": 0,
                "total_delivered": 0,
                "total_expired": 0,
                "cross_channel_deliveries": 0,
            },
        }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def gen_request_id(channel, topic, timestamp):
    """Generate a short deterministic ID for a request."""
    raw = f"{channel}:{topic}:{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def normalize_topic(topic):
    """Normalize topic text for fuzzy matching."""
    if not topic:
        return ""
    # lowercase, strip punctuation, collapse whitespace
    t = topic.lower().strip()
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# Common stop words to exclude from matching
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "up", "about", "into", "through",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "this", "that", "these", "those", "it", "its", "my", "your", "our",
    "their", "we", "you", "he", "she", "they", "me", "him", "her", "us",
    "them", "what", "which", "who", "whom", "how", "when", "where", "why",
    "all", "each", "every", "some", "any", "few", "more", "most", "other",
    "just", "also", "very", "well", "back", "get", "got", "check", "need",
    "find", "look", "see", "results", "update", "help", "please",
}


def extract_keywords(text):
    """Extract meaningful keywords, removing stop words."""
    words = set(normalize_topic(text).split())
    keywords = words - STOP_WORDS
    return keywords if keywords else words  # fall back to all words if everything is stop words


def topic_similarity(a, b):
    """Word-overlap similarity score (0.0 - 1.0) using keyword extraction."""
    if not a or not b:
        return 0.0
    kw_a = extract_keywords(a)
    kw_b = extract_keywords(b)
    if not kw_a or not kw_b:
        return 0.0
    intersection = kw_a & kw_b
    union = kw_a | kw_b
    # Weighted: full Jaccard + bonus for covering all keywords of one side
    jaccard = len(intersection) / len(union)
    coverage = max(
        len(intersection) / len(kw_a) if kw_a else 0,
        len(intersection) / len(kw_b) if kw_b else 0,
    )
    return 0.6 * jaccard + 0.4 * coverage


def cmd_record(args):
    """Record a new request with its source channel."""
    state = load_state()
    ts = time.time()
    request_id = gen_request_id(args.channel, args.topic, ts)

    # Check for near-duplicate (same channel + high topic similarity)
    for rid, req in state["requests"].items():
        if req["channel"] == args.channel and topic_similarity(req["topic"], args.topic) > 0.8:
            print(f"⚠️  Similar request already tracked: {rid} — '{req['topic']}'")
            return

    state["requests"][request_id] = {
        "channel": args.channel,
        "chat_id": args.chat_id or "",
        "sender": args.sender or "",
        "topic": args.topic,
        "normalized_topic": normalize_topic(args.topic),
        "timestamp": ts,
        "iso": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        "priority": args.priority or "normal",
    }
    state["stats"]["total_recorded"] += 1
    save_state(state)

    channel_name = CHANNELS.get(args.channel, {}).get("name", args.channel)
    print(f"📥 Recorded request [{request_id}] from {channel_name}: '{args.topic}'")


def cmd_match(args):
    """Find which channel a topic was originally requested from."""
    state = load_state()
    query = normalize_topic(args.topic)
    matches = []

    for rid, req in state["requests"].items():
        sim = topic_similarity(query, req["normalized_topic"])
        if sim >= 0.3:  # Threshold for "related"
            matches.append((sim, rid, req))

    if not matches:
        print(f"No matching requests found for: '{args.topic}'")
        return

    matches.sort(key=lambda x: x[0], reverse=True)
    print(f"🔍 Found {len(matches)} matching request(s) for: '{args.topic}'")
    print()

    for sim, rid, req in matches[:5]:
        channel_name = CHANNELS.get(req["channel"], {}).get("name", req["channel"])
        age_h = (time.time() - req["timestamp"]) / 3600
        sender = f" from {req['sender']}" if req.get("sender") else ""
        chat = f" (chat: {req['chat_id'][:20]})" if req.get("chat_id") else ""

        print(f"  {'🟢' if sim > 0.7 else '🟡'} [{rid}] {channel_name}{sender}{chat}")
        print(f"    Topic: '{req['topic']}'")
        print(f"    Match: {sim:.0%} | Age: {age_h:.1f}h | Priority: {req.get('priority', 'normal')}")
        print()

    best = matches[0]
    best_req = best[2]
    best_channel = CHANNELS.get(best_req["channel"], {}).get("name", best_req["channel"])
    print(f"  → Deliver response to: {best_channel}", end="")
    if best_req.get("chat_id"):
        print(f" (chat: {best_req['chat_id'][:30]})")
    else:
        print()


def cmd_deliver(args):
    """Mark a request as delivered (response sent to origin)."""
    state = load_state()

    if args.request_id not in state["requests"]:
        # Check if already delivered
        if args.request_id in state["delivered"]:
            print(f"ℹ️  Request {args.request_id} was already delivered.")
            return
        print(f"❌ Request {args.request_id} not found.")
        return

    req = state["requests"].pop(args.request_id)
    delivery_channel = args.via_channel or req["channel"]

    state["delivered"][args.request_id] = {
        **req,
        "delivered_at": time.time(),
        "delivery_channel": delivery_channel,
        "response_time_s": time.time() - req["timestamp"],
        "cross_channel": delivery_channel != req["channel"],
    }

    state["stats"]["total_delivered"] += 1
    if delivery_channel != req["channel"]:
        state["stats"]["cross_channel_deliveries"] += 1

    # Prune delivered older than 7 days
    cutoff = time.time() - (7 * 86400)
    state["delivered"] = {
        k: v for k, v in state["delivered"].items()
        if v.get("delivered_at", 0) > cutoff
    }

    save_state(state)
    channel_name = CHANNELS.get(req["channel"], {}).get("name", req["channel"])
    print(f"✅ Delivered [{args.request_id}] — origin: {channel_name}, topic: '{req['topic']}'")


def cmd_pending(args):
    """Show all undelivered requests, grouped by channel."""
    state = load_state()
    pending = state.get("requests", {})

    if not pending:
        print("No pending requests. All caught up! ✨")
        return

    # Group by channel
    by_channel = {}
    for rid, req in pending.items():
        ch = req["channel"]
        if ch not in by_channel:
            by_channel[ch] = []
        by_channel[ch].append((rid, req))

    total = len(pending)
    print(f"📬 {total} pending request(s):\n")

    for channel, items in sorted(by_channel.items()):
        channel_name = CHANNELS.get(channel, {}).get("name", channel)
        print(f"  {channel_name} ({len(items)}):")
        for rid, req in sorted(items, key=lambda x: x[1]["timestamp"]):
            age_h = (time.time() - req["timestamp"]) / 3600
            sender = f" — {req['sender']}" if req.get("sender") else ""
            priority = f" [{req['priority'].upper()}]" if req.get("priority", "normal") != "normal" else ""
            stale = " ⚠️ STALE" if age_h > 24 else ""
            print(f"    [{rid}] '{req['topic']}'{sender}{priority} ({age_h:.1f}h ago){stale}")
        print()


def cmd_status(args):
    """Overview of request tracking state."""
    state = load_state()
    pending = state.get("requests", {})
    delivered = state.get("delivered", {})
    stats = state.get("stats", {})

    print("📊 Cross-Channel Request Tracker Status")
    print(f"  Pending: {len(pending)}")
    print(f"  Delivered (7d): {len(delivered)}")
    print(f"  Total recorded: {stats.get('total_recorded', 0)}")
    print(f"  Total delivered: {stats.get('total_delivered', 0)}")
    print(f"  Cross-channel: {stats.get('cross_channel_deliveries', 0)}")
    print(f"  Expired: {stats.get('total_expired', 0)}")

    if delivered:
        times = [v.get("response_time_s", 0) for v in delivered.values() if v.get("response_time_s")]
        if times:
            avg = sum(times) / len(times)
            print(f"  Avg response time: {avg / 3600:.1f}h")

    if pending:
        # Age distribution
        now = time.time()
        fresh = sum(1 for r in pending.values() if now - r["timestamp"] < 3600)
        recent = sum(1 for r in pending.values() if 3600 <= now - r["timestamp"] < 86400)
        stale = sum(1 for r in pending.values() if now - r["timestamp"] >= 86400)

        print(f"\n  Age distribution:")
        print(f"    <1h: {fresh} | 1-24h: {recent} | >24h (stale): {stale}")


def cmd_cleanup(args):
    """Expire old requests that are no longer relevant."""
    state = load_state()
    cutoff = time.time() - (args.hours * 3600)
    expired = []

    for rid, req in list(state["requests"].items()):
        if req["timestamp"] < cutoff:
            expired.append((rid, req))
            del state["requests"][rid]

    state["stats"]["total_expired"] += len(expired)

    # Also prune old delivered
    delivery_cutoff = time.time() - (7 * 86400)
    state["delivered"] = {
        k: v for k, v in state["delivered"].items()
        if v.get("delivered_at", 0) > delivery_cutoff
    }

    save_state(state)

    if expired:
        print(f"🗑️  Expired {len(expired)} request(s) older than {args.hours}h:")
        for rid, req in expired:
            channel_name = CHANNELS.get(req["channel"], {}).get("name", req["channel"])
            print(f"  [{rid}] {channel_name}: '{req['topic']}'")
    else:
        print(f"No requests older than {args.hours}h to expire.")


def main():
    parser = argparse.ArgumentParser(
        description="Cross-Channel Request/Response Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # record
    p_rec = sub.add_parser("record", help="Record a new request from a channel")
    p_rec.add_argument("--channel", required=True, choices=list(CHANNELS.keys()))
    p_rec.add_argument("--chat-id", default=None, help="Chat/thread/channel ID")
    p_rec.add_argument("--sender", default=None, help="Who made the request")
    p_rec.add_argument("--topic", required=True, help="Short description of what was requested")
    p_rec.add_argument("--priority", default="normal", choices=["low", "normal", "high", "urgent"])

    # match
    p_match = sub.add_parser("match", help="Find origin channel for a topic")
    p_match.add_argument("--topic", required=True, help="Topic to search for")

    # deliver
    p_del = sub.add_parser("deliver", help="Mark a request as delivered")
    p_del.add_argument("--request-id", required=True)
    p_del.add_argument("--via-channel", default=None, help="Channel used for delivery (if different from origin)")

    # pending
    sub.add_parser("pending", help="Show all undelivered requests")

    # status
    sub.add_parser("status", help="Overview stats")

    # cleanup
    p_clean = sub.add_parser("cleanup", help="Expire old entries")
    p_clean.add_argument("--hours", type=int, default=72, help="Expire requests older than N hours")

    args = parser.parse_args()

    if args.command == "record":
        cmd_record(args)
    elif args.command == "match":
        cmd_match(args)
    elif args.command == "deliver":
        cmd_deliver(args)
    elif args.command == "pending":
        cmd_pending(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
