#!/usr/bin/env python3
"""
Trello Board Sync — Cron job to review and update Trello boards.
Logs all actions with timestamps to daily rotating log files.

Usage: python3 trello-board-sync.py
Cron:  */30 * * * * python3 /home/ubu/.openclaw/workspace/scripts/trello-board-sync.py
"""

import json
import os
import sys
import keyring
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.path.expanduser("~/.openclaw/workspace/logs/trello"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_log_path():
    """Daily rotating log file."""
    today = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"trello-sync-{today}.log"

def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(get_log_path(), "a") as f:
        f.write(line + "\n")

def get_creds():
    api_key = keyring.get_password("openclaw", "TRELLO_API_KEY")
    token = keyring.get_password("openclaw", "TRELLO_TOKEN")
    if not api_key or not token:
        log("Missing Trello API credentials in keyring", "ERROR")
        sys.exit(1)
    return api_key, token

def trello_get(path, api_key, token, params=None):
    import urllib.request
    import urllib.parse
    base = "https://api.trello.com/1"
    p = {"key": api_key, "token": token}
    if params:
        p.update(params)
    url = f"{base}{path}?{urllib.parse.urlencode(p)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def main():
    log("=== Trello Board Sync started ===")
    api_key, token = get_creds()

    # Board IDs
    boards = {
        "To Do List": "TyFBN1Bx",
        "Customer Statuses": "DQTJSKgK",
        "Coconut Lessons": "bZudEKUZ",
    }

    for board_name, board_id in boards.items():
        try:
            lists = trello_get(f"/boards/{board_id}/lists", api_key, token,
                               {"cards": "all", "card_fields": "name,due,dueComplete,dateLastActivity,idList"})
            total_cards = sum(len(lst.get("cards", [])) for lst in lists)
            list_names = [lst["name"] for lst in lists]
            log(f"Board '{board_name}' ({board_id}): {total_cards} cards across {len(lists)} lists ({', '.join(list_names)})")

            # Check for overdue cards
            from datetime import datetime as dt
            now = dt.now(timezone.utc)
            for lst in lists:
                for card in lst.get("cards", []):
                    if card.get("due") and not card.get("dueComplete"):
                        due = dt.fromisoformat(card["due"].replace("Z", "+00:00"))
                        if due < now:
                            log(f"  OVERDUE: '{card['name']}' in list '{lst['name']}' (due {card['due']})", "WARN")

        except Exception as e:
            log(f"Error checking board '{board_name}': {e}", "ERROR")

    # Clean up old logs (keep 14 days)
    cutoff = datetime.now().strftime("%Y-%m-%d")
    for logfile in LOG_DIR.glob("trello-sync-*.log"):
        date_str = logfile.stem.replace("trello-sync-", "")
        try:
            from datetime import timedelta
            log_date = datetime.strptime(date_str, "%Y-%m-%d")
            if (datetime.now() - log_date).days > 14:
                logfile.unlink()
                log(f"Cleaned up old log: {logfile.name}")
        except ValueError:
            pass

    log("=== Trello Board Sync complete ===")

if __name__ == "__main__":
    main()
