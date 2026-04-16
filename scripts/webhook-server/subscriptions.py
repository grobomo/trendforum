#!/usr/bin/env python3
"""MS Graph Webhook Subscription Manager.

Creates and renews webhook subscriptions for:
- Teams chat messages (max 60 min expiry)
- Email inbox changes (max 4230 min / ~2.9 days expiry)

Usage:
    python3 subscriptions.py create --url https://your-funnel.ts.net/webhook
    python3 subscriptions.py list
    python3 subscriptions.py renew
    python3 subscriptions.py delete --id <subscription-id>
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [subscriptions] %(message)s",
)
log = logging.getLogger(__name__)

# Add msgraph lib
MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

from lib.msgraph.auth import TokenManager
from lib.msgraph.client import GraphClient

STATE_FILE = Path.home() / ".openclaw" / "webhook-server" / "subscriptions.json"
CONFIG_FILE = Path(__file__).parent.parent / "teams-poller" / "config.json"


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"subscriptions": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def create_subscription(client: GraphClient, resource: str, change_types: list,
                         notification_url: str, expiry_minutes: int,
                         client_state: str = "openclaw-webhook") -> dict | None:
    """Create a Graph webhook subscription."""
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

    payload = {
        "changeType": ",".join(change_types),
        "notificationUrl": notification_url,
        "resource": resource,
        "expirationDateTime": expiry.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
        "clientState": client_state,
    }

    try:
        result = client.post("/subscriptions", json=payload)
        log.info("Created subscription: id=%s resource=%s expires=%s",
                 result.get("id", "?"), resource, result.get("expirationDateTime", "?"))
        return result
    except Exception as e:
        log.error("Failed to create subscription for %s: %s", resource, e)
        return None


def renew_subscription(client: GraphClient, sub_id: str, expiry_minutes: int) -> dict | None:
    """Renew an existing subscription."""
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

    payload = {
        "expirationDateTime": expiry.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
    }

    try:
        result = client.patch(f"/subscriptions/{sub_id}", json=payload)
        log.info("Renewed subscription %s until %s", sub_id[:12], result.get("expirationDateTime", "?"))
        return result
    except Exception as e:
        log.error("Failed to renew subscription %s: %s", sub_id[:12], e)
        return None


def delete_subscription(client: GraphClient, sub_id: str) -> bool:
    """Delete a subscription."""
    try:
        client.delete(f"/subscriptions/{sub_id}")
        log.info("Deleted subscription %s", sub_id[:12])
        return True
    except Exception as e:
        log.error("Failed to delete subscription %s: %s", sub_id[:12], e)
        return False


def list_subscriptions(client: GraphClient) -> list:
    """List all active subscriptions."""
    try:
        result = client.get("/subscriptions")
        return result.get("value", [])
    except Exception as e:
        log.error("Failed to list subscriptions: %s", e)
        return []


def cmd_create(args):
    """Create subscriptions for Teams chats and email."""
    config = load_config()
    state = load_state()

    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.error("No valid Graph token")
        sys.exit(1)
    client = GraphClient(token=token)

    notification_url = args.url
    created = []

    # Teams chat subscriptions (max 60 min expiry for chat messages)
    chat_ids = []
    if config.get("chat_id"):
        chat_ids.append(config["chat_id"])
    if config.get("private_chat_id"):
        chat_ids.append(config["private_chat_id"])

    for chat_id in chat_ids:
        resource = f"/chats/{chat_id}/messages"
        sub = create_subscription(
            client, resource,
            change_types=["created"],
            notification_url=notification_url,
            expiry_minutes=55,  # Renew before 60 min limit
        )
        if sub:
            created.append({
                "id": sub["id"],
                "resource": resource,
                "type": "teams",
                "expiry_minutes": 55,
                "expiration": sub.get("expirationDateTime"),
                "created": datetime.now(timezone.utc).isoformat(),
            })

    # Email subscription (max 4230 min / ~2.9 days)
    resource = "/me/mailFolders('Inbox')/messages"
    sub = create_subscription(
        client, resource,
        change_types=["created"],
        notification_url=notification_url,
        expiry_minutes=4200,  # ~2.9 days, renew before 4230 limit
    )
    if sub:
        created.append({
            "id": sub["id"],
            "resource": resource,
            "type": "email",
            "expiry_minutes": 4200,
            "expiration": sub.get("expirationDateTime"),
            "created": datetime.now(timezone.utc).isoformat(),
        })

    state["subscriptions"] = created
    state["notification_url"] = notification_url
    state["last_created"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f"\nCreated {len(created)} subscription(s):")
    for s in created:
        print(f"  {s['type']:8} {s['id'][:12]}... expires {s['expiration']}")


def cmd_renew(args):
    """Renew all tracked subscriptions."""
    state = load_state()

    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.error("No valid Graph token")
        sys.exit(1)
    client = GraphClient(token=token)

    renewed = 0
    for sub in state.get("subscriptions", []):
        result = renew_subscription(client, sub["id"], sub.get("expiry_minutes", 55))
        if result:
            sub["expiration"] = result.get("expirationDateTime")
            renewed += 1
        else:
            # Subscription may have expired — recreate
            log.warning("Subscription %s may have expired, attempting recreate", sub["id"][:12])
            notification_url = state.get("notification_url", "")
            if notification_url:
                new_sub = create_subscription(
                    client, sub["resource"],
                    change_types=["created"],
                    notification_url=notification_url,
                    expiry_minutes=sub.get("expiry_minutes", 55),
                )
                if new_sub:
                    sub["id"] = new_sub["id"]
                    sub["expiration"] = new_sub.get("expirationDateTime")
                    renewed += 1

    state["last_renewed"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    log.info("Renewed %d/%d subscriptions", renewed, len(state.get("subscriptions", [])))


def cmd_list(args):
    """List active subscriptions."""
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.error("No valid Graph token")
        sys.exit(1)
    client = GraphClient(token=token)

    subs = list_subscriptions(client)
    if not subs:
        print("No active subscriptions")
        return

    print(f"\n{len(subs)} active subscription(s):")
    for s in subs:
        print(f"  {s.get('id', '?')[:12]}... resource={s.get('resource', '?')} "
              f"expires={s.get('expirationDateTime', '?')}")


def cmd_delete(args):
    """Delete a specific subscription."""
    tm = TokenManager()
    token = tm.get_token()
    if not token:
        log.error("No valid Graph token")
        sys.exit(1)
    client = GraphClient(token=token)

    if args.all:
        subs = list_subscriptions(client)
        for s in subs:
            delete_subscription(client, s["id"])
        state = load_state()
        state["subscriptions"] = []
        save_state(state)
        print(f"Deleted {len(subs)} subscription(s)")
    elif args.id:
        delete_subscription(client, args.id)
    else:
        print("Specify --id <subscription-id> or --all")


def main():
    parser = argparse.ArgumentParser(description="MS Graph Webhook Subscriptions")
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create subscriptions")
    p_create.add_argument("--url", required=True, help="Public webhook URL (HTTPS)")

    p_renew = sub.add_parser("renew", help="Renew all subscriptions")

    p_list = sub.add_parser("list", help="List active subscriptions")

    p_delete = sub.add_parser("delete", help="Delete subscriptions")
    p_delete.add_argument("--id", help="Subscription ID to delete")
    p_delete.add_argument("--all", action="store_true", help="Delete all subscriptions")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args)
    elif args.command == "renew":
        cmd_renew(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "delete":
        cmd_delete(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
