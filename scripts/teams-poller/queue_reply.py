#!/usr/bin/env python3
"""Queue a reply for the Teams service to post.

Usage:
    echo "reply text" | python3 queue_reply.py
    echo "reply text" | python3 queue_reply.py --chat-id 19:abc123@thread.v2
    python3 queue_reply.py < /tmp/reply.txt
    python3 queue_reply.py --chat-id 19:abc123@thread.v2 < /tmp/reply.txt

Reply body is ALWAYS read from stdin. Never from positional args.
This prevents the bug where a chat name passed as an arg gets posted as the message.
"""
import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
OUTBOUND_QUEUE = Path.home() / ".openclaw" / "teams-poller" / "outbound_queue.json"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_chat_access(config: dict, chat_id: str) -> str:
    """Return access policy for a chat_id ('read-only' or 'read-write')."""
    for c in config.get("chats", []):
        if c.get("id") == chat_id:
            return c.get("access", "read-write")
    return "read-write"


def get_chat_id_by_label(config: dict, label: str) -> str:
    """Look up chat_id by label (case-insensitive partial match)."""
    label_lower = label.lower()
    for c in config.get("chats", []):
        if c.get("label", "").lower() == label_lower:
            return c.get("id", "")
    # Partial match fallback
    for c in config.get("chats", []):
        if label_lower in c.get("label", "").lower():
            return c.get("id", "")
    return ""


# --- Parse args ---
# Only --chat-id or --chat (with value) is accepted. Everything else is rejected.
target_chat_id = ""
i = 1
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg in ("--chat-id", "--chat") and i + 1 < len(sys.argv):
        target_chat_id = sys.argv[i + 1]
        i += 2
    else:
        print(f"ERROR: Unknown argument '{arg}'. Reply body must come from stdin.", file=sys.stderr)
        print(f"Usage: echo 'reply text' | python3 {sys.argv[0]} [--chat-id <id>]", file=sys.stderr)
        sys.exit(1)

# --- Read reply from stdin ONLY ---
reply = sys.stdin.read().strip()

if not reply:
    print("No reply to queue (stdin was empty)")
    sys.exit(0)

if reply == "TEAMS_NO_REPLY":
    print("No reply to queue (TEAMS_NO_REPLY)")
    sys.exit(0)

# SAFETY: reject flag strings or file paths that leaked from compose step
_FLAG_RE = re.compile(r'^--[a-z]', re.IGNORECASE)
FLAG_PATTERNS = ['--file ', '--output ', '--path ', '/tmp/', '--flag']


def looks_like_flag(text: str) -> bool:
    stripped = text.strip().split('\n')[0]  # check first line
    if _FLAG_RE.match(stripped):
        return True
    return any(stripped.startswith(p) for p in FLAG_PATTERNS)


if looks_like_flag(reply):
    print(f"BLOCKED: reply looks like a leaked flag/path, not message content: {reply[:80]}")
    sys.exit(1)

# ── Enforce 🌴 bookends (SOUL.md contract) ──
# Every outbound Teams message MUST start and end with 🌴.
# This is enforced here so no compose path can bypass it.
PALM = "\U0001f334"  # 🌴
if not reply.startswith(PALM):
    reply = f"{PALM} {reply}"
if not reply.rstrip().endswith(PALM):
    reply = f"{reply.rstrip()} {PALM}"

# --- Resolve chat target ---
config = load_config()

# If target looks like a label (not a Teams chat ID), resolve it
if target_chat_id and not target_chat_id.startswith("19:"):
    resolved = get_chat_id_by_label(config, target_chat_id)
    if resolved:
        target_chat_id = resolved
    else:
        print(f"ERROR: Could not resolve chat label '{target_chat_id}' to a chat ID.", file=sys.stderr)
        sys.exit(1)

# Fall back to last inbound chat if no explicit target
if not target_chat_id:
    try:
        with open(OUTBOUND_QUEUE.parent / "last_inbound_chat.json") as f:
            target_chat_id = json.load(f).get("chat_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

if not target_chat_id:
    print("ERROR: No chat target — no --chat-id provided and no last_inbound_chat.json found.", file=sys.stderr)
    sys.exit(1)

# SAFETY: block replies to read-only chats
if get_chat_access(config, target_chat_id) == "read-only":
    chat_label = next(
        (c.get("label", "?") for c in config.get("chats", []) if c.get("id") == target_chat_id),
        "unknown"
    )
    print(f"BLOCKED: cannot post to read-only chat '{chat_label}'. Relay to Joel via Slack DM instead.")
    sys.exit(1)

# --- Queue the reply (array-based, supports multiple pending) ---
OUTBOUND_QUEUE.parent.mkdir(parents=True, exist_ok=True)

# Read existing queue (may be single-object legacy or array)
existing = []
try:
    with open(OUTBOUND_QUEUE) as f:
        data = json.load(f)
        if isinstance(data, list):
            existing = data
        elif isinstance(data, dict) and data.get("reply"):
            existing = [data]  # migrate legacy single-object
except (FileNotFoundError, json.JSONDecodeError):
    pass

existing.append({
    "reply": reply,
    "chat_id": target_chat_id,
    "timestamp": datetime.now(timezone.utc).isoformat(),
})

with open(OUTBOUND_QUEUE, "w") as f:
    json.dump(existing, f, indent=2)

chat_label = next(
    (c.get("label", "?") for c in config.get("chats", []) if c.get("id") == target_chat_id),
    target_chat_id[:30]
)
print(f"Reply queued for posting to '{chat_label}'")

# --- Mark all pending messages in this chat as responded (central tracker) ---
try:
    _tracker_dir = str(Path.home() / ".openclaw" / "workspace" / "scripts")
    if _tracker_dir not in sys.path:
        sys.path.insert(0, _tracker_dir)
    from teams_tracker.tracker import TeamsTracker
    TeamsTracker().record_response(chat_id=target_chat_id)
except Exception:
    pass  # Don't block reply queuing on tracker errors
