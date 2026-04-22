#!/usr/bin/env python3
"""Schedule Briefing Data Gatherer.

Pulls data from five sources and outputs structured JSON for the agent to analyze:
1. Trello Todo List board
2. Trello company/customer boards
3. Email (unread + recent)
4. Teams chats (recent messages across all read-enabled chats)
5. Outlook calendar events (today through next week)

Usage:
    python3 gather.py              # all sources
    python3 gather.py --source calendar,trello  # specific sources
"""

import json
import logging
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [schedule-briefing] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────

MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

SCRIPT_DIR = Path(__file__).parent
WORKSPACE = Path.home() / ".openclaw" / "workspace"
TEAMS_CONFIG = WORKSPACE / "scripts" / "teams-poller" / "config.json"

# ── Trello Config ────────────────────────────────────────────────

TODO_BOARD_ID = "TyFBN1Bx"

# Company/customer boards (by name pattern — excludes internal/utility boards)
INTERNAL_BOARDS = {
    "To Do List", "Coconut Lessons", "DD Lab - Task Tracker",
    "Comm Tracking", "CXTA template", "CXTA Template", "Test",
    "UX Ideas", "Customers overview", "Customer Statuses",
    "GM2S1 Account Investigation", "GM2S1 Accounts",
    "Squad Projects/opptys", "CEGP Customer Feedback",
}

# ── Helpers ──────────────────────────────────────────────────────

def get_trello_creds():
    """Get Trello API credentials from keyring."""
    import keyring
    key = keyring.get_password("openclaw", "TRELLO_API_KEY")
    token = keyring.get_password("openclaw", "TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError("Trello creds not found in keyring")
    return key, token


def trello_get(path, key, token, **params):
    """Make a Trello API GET request."""
    import requests
    params["key"] = key
    params["token"] = token
    url = f"https://api.trello.com/1{path}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_graph_client():
    """Initialize Graph API client."""
    from lib.msgraph.auth import TokenManager
    from lib.msgraph.client import GraphClient
    tm = TokenManager()
    token = tm.get_token()
    return GraphClient(token)


# ── Source: Trello Todo Board ────────────────────────────────────

def gather_trello_todo(key, token):
    """Get all open cards from the Todo List board with list names."""
    log.info("Gathering Trello Todo board...")
    try:
        lists = trello_get(f"/boards/{TODO_BOARD_ID}/lists", key, token,
                           filter="open", fields="name")
        list_map = {l["id"]: l["name"] for l in lists}

        cards = trello_get(f"/boards/{TODO_BOARD_ID}/cards", key, token,
                           filter="open",
                           fields="name,desc,due,dueComplete,labels,idList,dateLastActivity,shortUrl")

        result = []
        for c in cards:
            result.append({
                "name": c.get("name"),
                "list": list_map.get(c.get("idList"), "?"),
                "desc": (c.get("desc") or "")[:300],
                "due": c.get("due"),
                "dueComplete": c.get("dueComplete", False),
                "labels": [l.get("name", l.get("color", "")) for l in c.get("labels", [])],
                "lastActivity": c.get("dateLastActivity"),
                "url": c.get("shortUrl"),
            })
        return {"ok": True, "cards": result, "lists": [l["name"] for l in lists]}
    except Exception as e:
        log.error(f"Trello todo error: {e}")
        return {"ok": False, "error": str(e)}


# ── Source: Trello Company Boards ────────────────────────────────

def gather_trello_companies(key, token):
    """Get recent activity from customer/company boards."""
    log.info("Gathering Trello company boards...")
    try:
        boards = trello_get("/members/me/boards", key, token,
                            filter="open", fields="name,id,dateLastActivity")

        company_boards = [b for b in boards if b["name"] not in INTERNAL_BOARDS]

        results = []
        for b in company_boards:
            # Get open cards with recent activity (last 7 days)
            try:
                cards = trello_get(f"/boards/{b['id']}/cards", key, token,
                                   filter="open",
                                   fields="name,due,dueComplete,labels,idList,dateLastActivity")
                # Only include boards with cards
                if cards:
                    board_lists = trello_get(f"/boards/{b['id']}/lists", key, token,
                                             filter="open", fields="name")
                    list_map = {l["id"]: l["name"] for l in board_lists}

                    card_summaries = []
                    for c in cards:
                        card_summaries.append({
                            "name": c.get("name"),
                            "list": list_map.get(c.get("idList"), "?"),
                            "due": c.get("due"),
                            "dueComplete": c.get("dueComplete", False),
                            "labels": [l.get("name", l.get("color", "")) for l in c.get("labels", [])],
                            "lastActivity": c.get("dateLastActivity"),
                        })

                    results.append({
                        "board": b["name"],
                        "boardId": b["id"],
                        "lastActivity": b.get("dateLastActivity"),
                        "cardCount": len(cards),
                        "cards": card_summaries,
                    })
            except Exception as e:
                log.warning(f"Error reading board {b['name']}: {e}")

        return {"ok": True, "boards": results}
    except Exception as e:
        log.error(f"Trello companies error: {e}")
        return {"ok": False, "error": str(e)}


# ── Source: Email ────────────────────────────────────────────────

def gather_email(client):
    """Get recent and unread emails."""
    log.info("Gathering emails...")
    try:
        # Unread emails (top 20)
        unread = client.get(
            "/me/mailFolders/inbox/messages"
            "?$filter=isRead eq false"
            "&$orderby=receivedDateTime desc"
            "&$top=20"
            "&$select=subject,from,receivedDateTime,importance,isRead,bodyPreview,hasAttachments"
        )

        # Recent emails (last 24h, top 15)
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent = client.get(
            f"/me/mailFolders/inbox/messages"
            f"?$filter=receivedDateTime ge {since}"
            f"&$orderby=receivedDateTime desc"
            f"&$top=15"
            f"&$select=subject,from,receivedDateTime,importance,isRead,bodyPreview,hasAttachments"
        )

        def format_emails(msgs):
            result = []
            for m in msgs.get("value", []):
                result.append({
                    "subject": m.get("subject"),
                    "from": m.get("from", {}).get("emailAddress", {}).get("name", "?"),
                    "fromEmail": m.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "received": m.get("receivedDateTime"),
                    "importance": m.get("importance"),
                    "isRead": m.get("isRead"),
                    "preview": (m.get("bodyPreview") or "")[:200],
                    "hasAttachments": m.get("hasAttachments"),
                })
            return result

        return {
            "ok": True,
            "unread": format_emails(unread),
            "unreadCount": len(unread.get("value", [])),
            "recent24h": format_emails(recent),
        }
    except Exception as e:
        log.error(f"Email error: {e}")
        return {"ok": False, "error": str(e)}


# ── Source: Teams ────────────────────────────────────────────────

def gather_teams(client):
    """Get recent messages from all monitored Teams chats."""
    log.info("Gathering Teams messages...")
    try:
        # Load teams config for chat list
        with open(TEAMS_CONFIG) as f:
            config = json.load(f)

        since = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        results = []

        for chat in config.get("chats", []):
            if chat.get("access") == "disabled":
                continue

            chat_id = chat["id"]
            label = chat.get("label", chat_id[:20])

            try:
                msgs = client.get(
                    f"/chats/{chat_id}/messages"
                    f"?$top=10"
                    f"&$orderby=createdDateTime desc"
                )

                recent_msgs = []
                for m in msgs.get("value", []):
                    if m.get("messageType") != "message":
                        continue
                    created = m.get("createdDateTime", "")
                    if created < since:
                        continue
                    sender = m.get("from", {}).get("user", {}).get("displayName", "?")
                    body_text = m.get("body", {}).get("content", "")
                    # Strip HTML tags roughly
                    import re
                    body_text = re.sub(r'<[^>]+>', '', body_text).strip()
                    if len(body_text) > 300:
                        body_text = body_text[:300] + "..."

                    recent_msgs.append({
                        "sender": sender,
                        "time": created,
                        "text": body_text,
                    })

                if recent_msgs:
                    results.append({
                        "chat": label,
                        "access": chat.get("access"),
                        "messages": recent_msgs,
                    })
            except Exception as e:
                log.warning(f"Error reading chat {label}: {e}")

        return {"ok": True, "chats": results}
    except Exception as e:
        log.error(f"Teams error: {e}")
        return {"ok": False, "error": str(e)}


# ── Source: Calendar ─────────────────────────────────────────────

def gather_calendar(client):
    """Get calendar events for today through end of next week."""
    log.info("Gathering calendar events...")
    try:
        now = datetime.now(timezone.utc)
        # Start of today (UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # End of next week (Sunday)
        days_until_next_sunday = (6 - now.weekday()) + 7  # rest of this week + all of next
        end_date = today_start + timedelta(days=days_until_next_sunday + 1)

        start_str = today_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        resp = client.get(
            f"/me/calendarView"
            f"?startDateTime={start_str}"
            f"&endDateTime={end_str}"
            f"&$orderby=start/dateTime"
            f"&$top=100"
            f"&$select=subject,start,end,location,organizer,attendees,isAllDay,isCancelled,showAs,bodyPreview,importance"
        )

        events = []
        for e in resp.get("value", []):
            if e.get("isCancelled"):
                continue
            attendee_names = [
                a.get("emailAddress", {}).get("name", "?")
                for a in e.get("attendees", [])[:10]  # cap at 10 names
            ]
            events.append({
                "subject": e.get("subject"),
                "start": e["start"]["dateTime"],
                "end": e["end"]["dateTime"],
                "timeZone": e["start"].get("timeZone", "UTC"),
                "isAllDay": e.get("isAllDay", False),
                "organizer": e.get("organizer", {}).get("emailAddress", {}).get("name", "?"),
                "location": e.get("location", {}).get("displayName", ""),
                "attendeeCount": len(e.get("attendees", [])),
                "attendees": attendee_names,
                "showAs": e.get("showAs", ""),
                "preview": (e.get("bodyPreview") or "")[:150],
                "importance": e.get("importance"),
            })

        return {"ok": True, "events": events, "range": {"start": start_str, "end": end_str}}
    except Exception as e:
        log.error(f"Calendar error: {e}")
        return {"ok": False, "error": str(e)}


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Schedule Briefing Data Gatherer")
    parser.add_argument("--source", type=str, default="all",
                        help="Comma-separated sources: trello_todo,trello_companies,email,teams,calendar (or 'all')")
    args = parser.parse_args()

    sources = args.source.split(",") if args.source != "all" else [
        "trello_todo", "trello_companies", "email", "teams", "calendar"
    ]

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources_requested": sources,
    }

    # Init clients as needed
    graph_client = None
    trello_key, trello_token = None, None

    if any(s.startswith("trello") for s in sources):
        trello_key, trello_token = get_trello_creds()

    if any(s in sources for s in ["email", "teams", "calendar"]):
        graph_client = get_graph_client()

    # Gather each source
    if "trello_todo" in sources:
        result["trello_todo"] = gather_trello_todo(trello_key, trello_token)

    if "trello_companies" in sources:
        result["trello_companies"] = gather_trello_companies(trello_key, trello_token)

    if "email" in sources:
        result["email"] = gather_email(graph_client)

    if "teams" in sources:
        result["teams"] = gather_teams(graph_client)

    if "calendar" in sources:
        result["calendar"] = gather_calendar(graph_client)

    # Output as JSON to stdout
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
