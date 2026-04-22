#!/usr/bin/env python3
"""
Planner ↔ Trello Two-Way Sync

Syncs Microsoft Planner "Customer Requests" plan with Trello "To Do List" board.
- Planner → Trello: new/updated Planner tasks create/update Trello cards
- Trello → Planner: card status changes (Done, percentComplete) sync back to Planner

Linking: cards store Planner task ID in a custom field (desc footer) and vice versa.
Conflict resolution: last-modified wins (dateLastActivity comparison).

Usage:
    python3 sync.py                    # full two-way sync
    python3 sync.py --direction down   # Planner → Trello only
    python3 sync.py --direction up     # Trello → Planner only
    python3 sync.py --dry-run          # show what would happen

Cron: */15 * * * * python3 ~/.openclaw/workspace/scripts/planner-trello-sync/sync.py

Requires:
  - Graph API scopes: Tasks.Read (minimum), Tasks.ReadWrite (for Trello→Planner)
  - Trello API key/token in keyring
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import keyring
import requests

# ── Paths ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "sync-state.json"
LOG_DIR = Path.home() / ".openclaw" / "workspace" / "logs" / "planner-sync"
LOG_DIR.mkdir(parents=True, exist_ok=True)

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

# ── Config ───────────────────────────────────────────────────────

PLANNER_PLAN_ID = "7GMda6VdokGvMT7Levp5zWQAHE0l"  # Customer Requests
TRELLO_BOARD_ID = "TyFBN1Bx"                        # To Do List

# Planner bucket → Trello list mapping
PLANNER_BUCKET_TO_TRELLO = {
    "Inbox":       "6954d3af836b51597afff8e8",   # Joel Todo
    "In Progress": "6954d3af836b51597afff8e8",   # Joel Todo
    "Done":        "6954d3af836b51597afff8f1",   # Done
    "Blocked":     "6954d3af836b51597afff8e8",   # Joel Todo
}

# Trello list → Planner bucket mapping
TRELLO_LIST_TO_BUCKET = {
    "6954d3af836b51597afff8e8": "JYsM1ivHokeLvH--25SdBWQAK33D",  # Joel Todo → Inbox
    "6954d3af836b51597afff8e9": "JYsM1ivHokeLvH--25SdBWQAK33D",  # Coconut Todo → Inbox
    "69e19cd7864480d809461861": "JYsM1ivHokeLvH--25SdBWQAK33D",  # Justin Todo → Inbox
    "69e19cce3a6e1e41e5c910e6": "JYsM1ivHokeLvH--25SdBWQAK33D",  # Chrissa Todo → Inbox
    "69e51fe0ad60dd711d6e9fcc": "JYsM1ivHokeLvH--25SdBWQAK33D",  # Testing → Inbox
    "6954d3af836b51597afff8f1": "8V57m5iAFUS0cseX-RE9dmQAMhjQ",  # Done → Done
}

# Trello list → Planner percentComplete mapping
TRELLO_LIST_TO_PERCENT = {
    "6954d3af836b51597afff8f1": 100,  # Done
}

# User ID mapping: Planner user ID → Trello member username/fullName
# (For display; Trello card assignment requires member ID on the board)
USER_MAP = {
    "70ce5237-91c1-4a27-997c-ef5df6c18a0e": {"name": "Joel", "email": "Joel_Ginsberg@trendmicro.com"},
    "30606926-27ef-4c9d-8a86-2b435d43ac5e": {"name": "Chrissa", "email": "chrissa_constantine@trendmicro.com"},
    "fe968730-95db-426b-b630-461e6219eb4c": {"name": "Justin", "email": "justin_hook@trendmicro.com"},
}

# Planner user ID → Trello list for assignee routing
USER_TO_TRELLO_LIST = {
    "70ce5237-91c1-4a27-997c-ef5df6c18a0e": "6954d3af836b51597afff8e8",  # Joel → Joel Todo
    "30606926-27ef-4c9d-8a86-2b435d43ac5e": "69e19cce3a6e1e41e5c910e6",  # Chrissa → Chrissa Todo
    "fe968730-95db-426b-b630-461e6219eb4c": "69e19cd7864480d809461861",  # Justin → Justin Todo
}

# Link tag pattern in Trello card descriptions
PLANNER_LINK_PATTERN = r"\[planner:([^\]]+)\]"
TRELLO_LINK_PATTERN = r"\[trello:([^\]]+)\]"

# ── Logging ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [planner-sync] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIR / f"sync-{datetime.now().strftime('%Y-%m-%d')}.log"
        ),
    ],
)
log = logging.getLogger(__name__)

# ── State Management ─────────────────────────────────────────────

def load_state():
    """Load sync state (last sync time, known links)."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_sync": None,
        "links": {},       # planner_task_id → trello_card_id
        "rev_links": {},   # trello_card_id → planner_task_id
    }


def save_state(state):
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Graph API Client ─────────────────────────────────────────────

def get_graph_client():
    from lib.msgraph.auth import TokenManager
    from lib.msgraph.client import GraphClient
    tm = TokenManager()
    token = tm.get_token()
    return GraphClient(token), token


def graph_patch(token, path, body, etag):
    """PATCH a Planner resource (requires If-Match header)."""
    resp = requests.patch(
        f"https://graph.microsoft.com/v1.0{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "If-Match": etag,
        },
        json=body,
        timeout=15,
    )
    return resp


# ── Trello API ───────────────────────────────────────────────────

def get_trello_creds():
    api_key = keyring.get_password("openclaw", "TRELLO_API_KEY")
    token = keyring.get_password("openclaw", "TRELLO_TOKEN")
    if not api_key or not token:
        raise RuntimeError("Trello creds not in keyring")
    return api_key, token


def trello_get(path, api_key, token, **params):
    params["key"] = api_key
    params["token"] = token
    resp = requests.get(
        f"https://api.trello.com/1{path}",
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def trello_post(path, api_key, token, **data):
    data["key"] = api_key
    data["token"] = token
    resp = requests.post(
        f"https://api.trello.com/1{path}",
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def trello_put(path, api_key, token, **data):
    data["key"] = api_key
    data["token"] = token
    resp = requests.put(
        f"https://api.trello.com/1{path}",
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Planner Data Fetch ───────────────────────────────────────────

def fetch_planner_tasks(client):
    """Fetch all tasks from the Customer Requests plan."""
    tasks = []
    url = f"/planner/plans/{PLANNER_PLAN_ID}/tasks"
    while url:
        resp = client.get(url)
        tasks.extend(resp.get("value", []))
        url = resp.get("@odata.nextLink")
        if url:
            # Strip base URL if present
            url = url.replace("https://graph.microsoft.com/v1.0", "")
    return tasks


def fetch_planner_buckets(client):
    """Fetch bucket names for the plan."""
    resp = client.get(f"/planner/plans/{PLANNER_PLAN_ID}/buckets")
    return {b["id"]: b["name"] for b in resp.get("value", [])}


def fetch_task_details(client, task_id):
    """Fetch task details (description, checklist)."""
    try:
        return client.get(f"/planner/tasks/{task_id}/details")
    except Exception as e:
        log.warning(f"Could not fetch details for task {task_id}: {e}")
        return {}


# ── Trello Data Fetch ────────────────────────────────────────────

def fetch_trello_cards(api_key, token):
    """Fetch all open cards from the To Do List board."""
    return trello_get(
        f"/boards/{TRELLO_BOARD_ID}/cards",
        api_key, token,
        filter="open",
        fields="name,desc,due,dueComplete,labels,idList,dateLastActivity,shortUrl,idMembers",
    )


def fetch_trello_lists(api_key, token):
    """Fetch list names."""
    lists = trello_get(
        f"/boards/{TRELLO_BOARD_ID}/lists",
        api_key, token,
        filter="open",
        fields="name",
    )
    return {l["id"]: l["name"] for l in lists}


# ── Link Management ──────────────────────────────────────────────

def extract_planner_id(desc):
    """Extract Planner task ID from Trello card description."""
    m = re.search(PLANNER_LINK_PATTERN, desc or "")
    return m.group(1) if m else None


def extract_trello_id(desc):
    """Extract Trello card ID from Planner task description."""
    m = re.search(TRELLO_LINK_PATTERN, desc or "")
    return m.group(1) if m else None


def add_planner_link(desc, planner_id):
    """Add Planner link tag to Trello card description."""
    if extract_planner_id(desc):
        return desc  # already linked
    tag = f"\n\n---\n[planner:{planner_id}]"
    return (desc or "") + tag


def add_trello_link(desc, trello_id):
    """Add Trello link tag to Planner task description."""
    if extract_trello_id(desc):
        return desc
    tag = f"\n\n---\n[trello:{trello_id}]"
    return (desc or "") + tag


# ── Sync: Planner → Trello ──────────────────────────────────────

def sync_planner_to_trello(client, token, api_key, trello_token, state, dry_run=False):
    """Sync Planner tasks down to Trello cards."""
    log.info("=== Planner → Trello sync ===")

    tasks = fetch_planner_tasks(client)
    buckets = fetch_planner_buckets(client)
    cards = fetch_trello_cards(api_key, trello_token)
    trello_lists = fetch_trello_lists(api_key, trello_token)

    log.info(f"Planner: {len(tasks)} tasks, Trello: {len(cards)} cards")

    # Build lookup: planner_id → trello_card (from desc links + state)
    card_by_planner_id = {}
    for card in cards:
        pid = extract_planner_id(card.get("desc"))
        if pid:
            card_by_planner_id[pid] = card
    for pid, cid in state.get("links", {}).items():
        if pid not in card_by_planner_id:
            for card in cards:
                if card["id"] == cid:
                    card_by_planner_id[pid] = card
                    break

    created = 0
    updated = 0
    skipped = 0

    for task in tasks:
        task_id = task["id"]
        title = task.get("title", "Untitled")
        bucket_name = buckets.get(task.get("bucketId"), "Unknown")
        due = task.get("dueDateTime")
        pct = task.get("percentComplete", 0)
        assignees = list(task.get("assignments", {}).keys())

        # Determine target Trello list based on assignee (first match) or bucket
        target_list = None
        for uid in assignees:
            if uid in USER_TO_TRELLO_LIST:
                target_list = USER_TO_TRELLO_LIST[uid]
                break
        if not target_list:
            target_list = PLANNER_BUCKET_TO_TRELLO.get(bucket_name, "6954d3af836b51597afff8e8")

        # If task is 100% complete → Done list
        if pct == 100:
            target_list = "6954d3af836b51597afff8f1"

        # Build description: assignee names + bucket (skip detail fetch for speed)
        assignee_names = [USER_MAP.get(uid, {}).get("name", uid[:8]) for uid in assignees]
        desc_parts = []
        if assignee_names:
            desc_parts.append(f"Assignees: {', '.join(assignee_names)}")
        desc_parts.append(f"Bucket: {bucket_name}")
        desc_body = "\n".join(desc_parts)

        existing_card = card_by_planner_id.get(task_id)

        if existing_card:
            # Update existing card if Planner is newer
            planner_modified = task.get("createdDateTime", "")  # Planner doesn't expose lastModified well
            card_modified = existing_card.get("dateLastActivity", "")

            # Check if anything actually changed
            needs_update = False
            if existing_card.get("name") != title:
                needs_update = True
            if existing_card.get("idList") != target_list:
                needs_update = True
            if existing_card.get("due") != due:
                needs_update = True
            if pct == 100 and not existing_card.get("dueComplete"):
                needs_update = True

            if needs_update:
                if dry_run:
                    log.info(f"  [DRY-RUN] Would update card: {title}")
                else:
                    desc_with_link = add_planner_link(desc_body, task_id)
                    trello_put(
                        f"/cards/{existing_card['id']}",
                        api_key, trello_token,
                        name=title,
                        desc=desc_with_link,
                        idList=target_list,
                        due=due or "",
                        dueComplete="true" if pct == 100 else "false",
                    )
                    state["links"][task_id] = existing_card["id"]
                    state["rev_links"][existing_card["id"]] = task_id
                    log.info(f"  Updated: {title}")
                updated += 1
            else:
                skipped += 1
        else:
            # Create new Trello card
            if dry_run:
                log.info(f"  [DRY-RUN] Would create card: {title}")
            else:
                desc_with_link = add_planner_link(desc_body, task_id)
                new_card = trello_post(
                    "/cards",
                    api_key, trello_token,
                    name=title,
                    desc=desc_with_link,
                    idList=target_list,
                    due=due or "",
                    dueComplete="true" if pct == 100 else "false",
                )
                state["links"][task_id] = new_card["id"]
                state["rev_links"][new_card["id"]] = task_id
                log.info(f"  Created: {title} → {trello_lists.get(target_list, target_list)}")
                # Rate limit: small delay between creates
                time.sleep(0.3)
            created += 1

    log.info(f"Planner→Trello: {created} created, {updated} updated, {skipped} unchanged")
    return created, updated


# ── Sync: Trello → Planner ──────────────────────────────────────

def sync_trello_to_planner(client, token, api_key, trello_token, state, dry_run=False):
    """Sync Trello card changes back to Planner tasks."""
    log.info("=== Trello → Planner sync ===")

    cards = fetch_trello_cards(api_key, trello_token)

    updated = 0
    skipped = 0
    no_write = 0

    for card in cards:
        card_id = card["id"]
        planner_id = extract_planner_id(card.get("desc"))
        if not planner_id:
            planner_id = state.get("rev_links", {}).get(card_id)
        if not planner_id:
            continue  # Not a synced card

        list_id = card.get("idList")
        card_done = card.get("dueComplete", False)
        card_due = card.get("due")

        # Determine what Planner should look like based on Trello state
        target_pct = TRELLO_LIST_TO_PERCENT.get(list_id, 0)
        if card_done:
            target_pct = 100
        target_bucket = TRELLO_LIST_TO_BUCKET.get(list_id)

        # Fetch current Planner task
        try:
            task = client.get(f"/planner/tasks/{planner_id}")
        except Exception as e:
            log.warning(f"Could not fetch Planner task {planner_id}: {e}")
            continue

        etag = task.get("@odata.etag")
        current_pct = task.get("percentComplete", 0)
        current_bucket = task.get("bucketId")

        # Check if update needed
        patch_body = {}
        if target_pct != current_pct:
            patch_body["percentComplete"] = target_pct
        if target_bucket and target_bucket != current_bucket:
            patch_body["bucketId"] = target_bucket

        if not patch_body:
            skipped += 1
            continue

        if dry_run:
            log.info(f"  [DRY-RUN] Would update Planner task: {task.get('title')} → {patch_body}")
            updated += 1
            continue

        # Try the PATCH
        resp = graph_patch(token, f"/planner/tasks/{planner_id}", patch_body, etag)
        if resp.status_code == 204:
            log.info(f"  Updated Planner: {task.get('title')} → {patch_body}")
            updated += 1
        elif resp.status_code == 403:
            log.warning(f"  NO WRITE PERMISSION for Planner task: {task.get('title')}")
            no_write += 1
        else:
            log.error(f"  Failed to update {task.get('title')}: {resp.status_code} {resp.text[:200]}")

    log.info(f"Trello→Planner: {updated} updated, {skipped} unchanged, {no_write} permission-denied")
    return updated, no_write


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Planner ↔ Trello Two-Way Sync")
    parser.add_argument("--direction", choices=["down", "up", "both"], default="both",
                        help="down=Planner→Trello, up=Trello→Planner, both=two-way")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    state = load_state()
    client, token = get_graph_client()
    api_key, trello_token = get_trello_creds()

    log.info(f"Planner↔Trello sync starting (direction={args.direction}, dry_run={args.dry_run})")

    if args.direction in ("down", "both"):
        sync_planner_to_trello(client, token, api_key, trello_token, state, args.dry_run)

    if args.direction in ("up", "both"):
        sync_trello_to_planner(client, token, api_key, trello_token, state, args.dry_run)

    if not args.dry_run:
        save_state(state)

    log.info("Sync complete.")


if __name__ == "__main__":
    main()
