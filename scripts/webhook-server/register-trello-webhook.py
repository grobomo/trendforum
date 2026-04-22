#!/usr/bin/env python3
"""Register Trello webhooks for board change notifications.

Usage:
    python3 register-trello-webhook.py                    # Register Todo board
    python3 register-trello-webhook.py --board <id>       # Specific board
    python3 register-trello-webhook.py --list             # List existing webhooks
    python3 register-trello-webhook.py --delete <wh_id>   # Delete a webhook
"""

import argparse
import json
import sys

import keyring
import requests

API_BASE = "https://api.trello.com/1"
CALLBACK_URL = "https://nabu-2wd56m3-1.orca-decibel.ts.net/webhooks/trello"

# Default boards to watch
TODO_BOARD_ID = "TyFBN1Bx"


def get_creds():
    key = keyring.get_password("openclaw", "TRELLO_API_KEY")
    token = keyring.get_password("openclaw", "TRELLO_TOKEN")
    if not key or not token:
        print("ERROR: Trello creds not in keyring")
        sys.exit(1)
    return key, token


def list_webhooks(key, token):
    """List all registered webhooks."""
    # First get the token's member ID
    resp = requests.get(f"{API_BASE}/tokens/{token}/webhooks",
                        params={"key": key, "token": token}, timeout=15)
    resp.raise_for_status()
    webhooks = resp.json()
    if not webhooks:
        print("No webhooks registered.")
        return
    for wh in webhooks:
        active = "✅" if wh.get("active") else "❌"
        print(f"{active} {wh['id']} → {wh.get('description', '?')} | model: {wh['idModel']} | url: {wh['callbackURL']}")


def register_webhook(key, token, board_id, description=None):
    """Register a webhook for a board."""
    if not description:
        description = f"OpenClaw schedule briefing — board {board_id}"

    resp = requests.post(f"{API_BASE}/webhooks",
                         params={"key": key, "token": token},
                         json={
                             "callbackURL": CALLBACK_URL,
                             "idModel": board_id,
                             "description": description,
                             "active": True,
                         },
                         timeout=15)

    if resp.status_code == 200:
        wh = resp.json()
        print(f"✅ Webhook registered: {wh['id']}")
        print(f"   Board: {board_id}")
        print(f"   Callback: {CALLBACK_URL}")
        print(f"   Description: {description}")
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text}")


def delete_webhook(key, token, webhook_id):
    """Delete a webhook."""
    resp = requests.delete(f"{API_BASE}/webhooks/{webhook_id}",
                           params={"key": key, "token": token}, timeout=15)
    if resp.status_code == 200:
        print(f"✅ Deleted webhook {webhook_id}")
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Trello webhook manager")
    parser.add_argument("--board", type=str, help="Board ID to register webhook for")
    parser.add_argument("--list", action="store_true", help="List existing webhooks")
    parser.add_argument("--delete", type=str, help="Delete webhook by ID")
    parser.add_argument("--description", type=str, help="Webhook description")
    parser.add_argument("--all-company-boards", action="store_true",
                        help="Register webhooks for all company/customer boards")
    args = parser.parse_args()

    key, token = get_creds()

    if args.list:
        list_webhooks(key, token)
    elif args.delete:
        delete_webhook(key, token, args.delete)
    elif args.all_company_boards:
        # Get all boards and register webhooks for each
        resp = requests.get(f"{API_BASE}/members/me/boards",
                            params={"key": key, "token": token, "filter": "open", "fields": "name,id"},
                            timeout=15)
        resp.raise_for_status()
        boards = resp.json()
        for b in boards:
            register_webhook(key, token, b["id"], f"OpenClaw — {b['name']}")
    else:
        board_id = args.board or TODO_BOARD_ID
        register_webhook(key, token, board_id, args.description)


if __name__ == "__main__":
    main()
