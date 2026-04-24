#!/usr/bin/env python3
"""Dynamic Webhook Lifecycle Manager.

Scans Joel's Teams chats, auto-creates/removes webhook subscriptions based on activity.

Rules:
- Any chat active in last 24h → create webhook subscription if missing
- New/unknown chats → auto-create with read-only policy in openclaw-dm
- Chats inactive >24h → unsubscribe webhook
- Chats with monitoring:disabled in policy → skip (never subscribe)
- Runs on cron (every 15 min) to catch new/revived chats

Usage:
    python3 lifecycle.py scan          # Scan and report what needs changing
    python3 lifecycle.py sync          # Actually create/remove subscriptions
    python3 lifecycle.py sync --dry-run # Show what would change without doing it
"""

import argparse
import json
import logging
import os
import shutil
import sys
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [lifecycle] %(message)s",
)
log = logging.getLogger(__name__)

sys.path.insert(0, os.path.expanduser("~/lib/teams-agent"))
from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient

DM_ROOT = Path(os.path.expanduser("~/openclaw-dm"))
DEFAULTS_POLICY = DM_ROOT / "_defaults" / "policy.yaml"
STATE_FILE = Path.home() / ".openclaw" / "webhook-server" / "subscriptions.json"
NOTIFICATION_URL = None  # Read from state file
LOG_FILE = DM_ROOT / "comms-preprocessor.log"


def load_notification_url() -> str:
    """Get webhook URL from subscription state."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get("notification_url", "")
    except Exception:
        return ""


def slugify(name: str) -> str:
    """Convert chat topic/name to directory-safe slug."""
    if not name:
        return ""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:60].strip('-')


def get_active_chats(client: GraphClient, hours: int = 24) -> list:
    """Get all Teams chats with activity in last N hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    all_chats = []
    try:
        result = client.get("/me/chats", params={
            "$expand": "lastMessagePreview",
            "$top": "50",
        })
        all_chats = result.get("value", [])
    except Exception as e:
        log.error("Failed to fetch chats: %s", e)
        return []
    
    active = []
    for c in all_chats:
        preview = c.get("lastMessagePreview", {})
        if not preview:
            continue
        
        last_msg_time = preview.get("createdDateTime", "")
        if not last_msg_time:
            continue
        
        try:
            t = datetime.fromisoformat(last_msg_time.replace("Z", "+00:00"))
            if t < since:
                continue
        except Exception:
            continue
        
        topic = c.get("topic", "")
        chat_type = c.get("chatType", "")
        chat_id = c.get("id", "")
        
        # Build a label from topic or chat participants
        if topic:
            label = slugify(topic)
        elif chat_type == "oneOnOne":
            # Try to get other person's name from lastMessagePreview
            sender = preview.get("from", {})
            user = sender.get("user", {}) if sender else {}
            name = user.get("displayName", "")
            if name and "Joel" not in name:
                label = f"dm-{slugify(name)}"
            else:
                label = f"dm-{chat_id[:12]}"
        else:
            label = f"chat-{chat_id[:12]}"
        
        active.append({
            "id": chat_id,
            "topic": topic,
            "type": chat_type,
            "label": label,
            "last_msg_time": last_msg_time,
            "last_msg_sender": (preview.get("from", {}) or {}).get("user", {}).get("displayName", ""),
        })
    
    return active


def get_existing_policies() -> dict:
    """Load all Teams policy files. Returns {chat_id: {label, policy}}."""
    policies = {}
    teams_dir = DM_ROOT / "teams"
    if not teams_dir.exists():
        return policies
    
    for chat_dir in teams_dir.iterdir():
        if not chat_dir.is_dir():
            continue
        pol_file = chat_dir / "policy.yaml"
        if pol_file.exists():
            try:
                with open(pol_file) as f:
                    pol = yaml.safe_load(f)
                chat_id = pol.get("chat_id", "")
                if chat_id:
                    policies[chat_id] = {
                        "label": chat_dir.name,
                        "policy": pol,
                        "dir": chat_dir,
                    }
            except Exception:
                pass
    return policies


def get_subscribed_chat_ids() -> set:
    """Get set of chat IDs that currently have webhook subscriptions."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        ids = set()
        for s in state.get("subscriptions", []):
            res = s.get("resource", "")
            if "/chats/" in res:
                cid = res.split("/chats/")[1].split("/")[0]
                ids.add(cid)
        return ids
    except Exception:
        return set()


def create_chat_dir(label: str, chat_id: str, topic: str, chat_type: str):
    """Create openclaw-dm directory for a new chat with default policy."""
    chat_dir = DM_ROOT / "teams" / label
    chat_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy default policy and customize
    default_pol = {}
    if DEFAULTS_POLICY.exists():
        with open(DEFAULTS_POLICY) as f:
            default_pol = yaml.safe_load(f) or {}
    
    policy = {
        "chat_id": chat_id,
        "monitoring": "enabled",
        "access": "read-only",
        "data_sensitivity": default_pol.get("data_sensitivity", "standard"),
        "response_priority": "normal",
        "auto_respond": False,
        "require_approval": True,
        "notes": f"Auto-discovered {datetime.now().strftime('%Y-%m-%d %H:%M')} | topic: {topic or '(none)'} | type: {chat_type}",
    }
    
    with open(chat_dir / "policy.yaml", "w") as f:
        yaml.dump(policy, f, default_flow_style=False, sort_keys=False)
    
    state = {
        "chat_id": chat_id,
        "platform": "teams",
        "type": chat_type,
        "name": topic or label,
        "created_in_state": datetime.now().strftime("%Y-%m-%d"),
        "last_webhook_received": None,
        "last_message_processed": None,
        "last_response_sent": None,
        "health_status": "unknown",
        "messages_since_last_response": 0,
        "recent_topics": [],
        "active_participants": [],
    }
    
    with open(chat_dir / "state.yaml", "w") as f:
        yaml.dump(state, f, default_flow_style=False, sort_keys=False)
    
    todo = f"# Todo: {topic or label}\n\n## Open\n\n_(none yet)_\n\n## Done\n\n_(none yet)_\n"
    with open(chat_dir / "todo.md", "w") as f:
        f.write(todo)
    
    log.info("Created new chat dir: teams/%s (chat_id=%s)", label, chat_id[:30])


def create_subscription(client: GraphClient, chat_id: str, url: str) -> str | None:
    """Create a webhook subscription for a chat. Returns subscription ID."""
    resource = f"/chats/{chat_id}/messages"
    expiry = datetime.now(timezone.utc) + timedelta(minutes=55)
    
    try:
        result = client.post("/subscriptions", body={
            "changeType": "created,updated",
            "notificationUrl": url,
            "resource": resource,
            "expirationDateTime": expiry.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
            "clientState": "openclaw-webhook",
        })
        sub_id = result.get("id", "")
        log.info("Created subscription %s for %s", sub_id[:12], chat_id[:30])
        return sub_id
    except Exception as e:
        log.error("Failed to subscribe to %s: %s", chat_id[:30], e)
        return None


def remove_subscription(client: GraphClient, sub_id: str) -> bool:
    """Delete a webhook subscription."""
    try:
        client.delete(f"/subscriptions/{sub_id}")
        log.info("Removed subscription %s", sub_id[:12])
        return True
    except Exception as e:
        log.error("Failed to remove subscription %s: %s", sub_id[:12], e)
        return False


def log_decision(action: str, label: str, chat_id: str, reason: str):
    """Append to central preprocessor log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] LIFECYCLE_{action} | teams/{label} | {reason} | chat_id={chat_id[:30]}\n")


def cmd_scan(args):
    """Scan and report what needs changing."""
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        print("ERROR: No Graph token")
        sys.exit(1)
    client = GraphClient(token=token)
    
    active_chats = get_active_chats(client, hours=24)
    existing_policies = get_existing_policies()
    subscribed_ids = get_subscribed_chat_ids()
    
    print(f"Active chats (24h): {len(active_chats)}")
    print(f"Existing policies: {len(existing_policies)}")
    print(f"Active subscriptions: {len(subscribed_ids)}")
    print()
    
    # Find chats needing new subscriptions
    need_sub = []
    need_dir = []
    for chat in active_chats:
        cid = chat["id"]
        
        # Check if monitoring is disabled
        if cid in existing_policies:
            pol = existing_policies[cid]["policy"]
            if pol.get("monitoring") == "disabled":
                continue
        
        if cid not in subscribed_ids:
            need_sub.append(chat)
        if cid not in existing_policies:
            need_dir.append(chat)
    
    if need_dir:
        print(f"NEW CHATS (need openclaw-dm dir): {len(need_dir)}")
        for c in need_dir:
            print(f"  {c['label']}: {c['topic'] or c['type']} | last: {c['last_msg_time'][:19]}")
    
    if need_sub:
        print(f"\nNEED WEBHOOKS: {len(need_sub)}")
        for c in need_sub:
            print(f"  {c['label']}: {c['topic'] or c['type']}")
    
    # Find subscriptions to remove (inactive chats)
    active_ids = {c["id"] for c in active_chats}
    disabled_ids = {cid for cid, p in existing_policies.items() if p["policy"].get("monitoring") == "disabled"}
    
    to_remove = subscribed_ids - active_ids - disabled_ids
    # Don't remove email subscriptions
    if to_remove:
        print(f"\nCOULD UNSUBSCRIBE (inactive >24h): {len(to_remove)}")
    
    if not need_sub and not need_dir:
        print("\nAll active chats are covered. ✅")


def cmd_sync(args):
    """Actually create/remove subscriptions."""
    url = load_notification_url()
    if not url:
        print("ERROR: No notification URL in subscription state")
        sys.exit(1)
    
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        print("ERROR: No Graph token")
        sys.exit(1)
    client = GraphClient(token=token)
    
    active_chats = get_active_chats(client, hours=24)
    existing_policies = get_existing_policies()
    subscribed_ids = get_subscribed_chat_ids()
    
    # Load state for updating
    with open(STATE_FILE) as f:
        state = json.load(f)
    
    created = 0
    discovered = 0
    
    for chat in active_chats:
        cid = chat["id"]
        label = chat["label"]
        
        # Check if monitoring disabled
        if cid in existing_policies:
            pol = existing_policies[cid]["policy"]
            label = existing_policies[cid]["label"]  # Use existing label
            if pol.get("monitoring") == "disabled":
                continue
        
        # Create dir if new chat
        if cid not in existing_policies:
            if args.dry_run:
                print(f"  [DRY RUN] Would create dir: teams/{label}")
            else:
                create_chat_dir(label, cid, chat.get("topic", ""), chat.get("type", ""))
                log_decision("NEW_CHAT", label, cid, f"Auto-discovered, topic={chat.get('topic', '')}")
                discovered += 1
        
        # Create subscription if missing
        if cid not in subscribed_ids:
            if args.dry_run:
                print(f"  [DRY RUN] Would subscribe: teams/{label}")
            else:
                sub_id = create_subscription(client, cid, url)
                if sub_id:
                    state["subscriptions"].append({
                        "id": sub_id,
                        "resource": f"/chats/{cid}/messages",
                        "type": "teams-messages",
                        "expiry_minutes": 55,
                        "expiration": (datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat(),
                        "created": datetime.now(timezone.utc).isoformat(),
                    })
                    log_decision("SUBSCRIBE", label, cid, "Active chat, webhook added")
                    created += 1
    
    if not args.dry_run:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    
    print(f"\nSync complete: {discovered} new chats discovered, {created} webhooks created")


def main():
    parser = argparse.ArgumentParser(description="Dynamic webhook lifecycle manager")
    sub = parser.add_subparsers(dest="command")
    
    scan_p = sub.add_parser("scan", help="Scan and report")
    
    sync_p = sub.add_parser("sync", help="Create/remove subscriptions")
    sync_p.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    
    args = parser.parse_args()
    
    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "sync":
        cmd_sync(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
