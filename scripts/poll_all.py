#!/usr/bin/env python3
"""Unified poller — runs all checks in one pass.

Runs Teams inbound check, GitHub poll, email poll, and Trello board check.
Only produces output if something needs attention.
Also checks Teams service health.

Usage:
    python3 poll_all.py
"""

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
results = []


def run_script(name, script_path):
    """Run a poller script and capture output."""
    try:
        r = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=60,
        )
        output = r.stdout.strip()
        if output:
            return output
    except subprocess.TimeoutExpired:
        return f"[{name} timed out]"
    except Exception as e:
        return f"[{name} error: {e}]"
    return None


# 1. Teams inbound queue check
teams_out = run_script("Teams", SCRIPT_DIR / "teams-poller/check_inbound.py")
if teams_out:
    results.append(("TEAMS", teams_out))

# 2. GitHub poll
gh_out = run_script("GitHub", SCRIPT_DIR / "github-poller/poll_github.py")
if gh_out:
    results.append(("GITHUB", gh_out))

# 3. Email poll
email_out = run_script("Email", SCRIPT_DIR / "email-poller/poll_email.py")
if email_out and "timed out" not in email_out:
    results.append(("EMAIL", email_out))

# 4. Trello board check
try:
    import keyring
    import requests
    api_key = keyring.get_password('openclaw', 'TRELLO_API_KEY')
    token = keyring.get_password('openclaw', 'TRELLO_TOKEN')
    if api_key and token:
        # Load last-seen state
        trello_state_file = Path.home() / '.openclaw' / 'trello-poller' / 'state.json'
        trello_state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(trello_state_file) as f:
                trello_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            trello_state = {'known_cards': {}, 'last_check': 0}

        r = requests.get(
            'https://api.trello.com/1/boards/TyFBN1Bx/lists',
            params={'key': api_key, 'token': token, 'cards': 'all',
                    'card_fields': 'name,desc,dueComplete,idList,dateLastActivity'},
            timeout=15
        )
        if r.status_code == 200:
            lists = r.json()
            known = trello_state.get('known_cards', {})
            changes = []
            current_cards = {}

            for lst in lists:
                for card in lst.get('cards', []):
                    cid = card['id']
                    current_cards[cid] = {
                        'name': card['name'],
                        'list': lst['name'],
                        'dueComplete': card.get('dueComplete', False),
                        'dateLastActivity': card.get('dateLastActivity', ''),
                    }
                    if cid not in known:
                        # Don't report date card as new
                        if cid != '69e5386452efe00168682d3f':
                            changes.append(f"NEW card in *{lst['name']}*: {card['name']}")
                    elif known[cid].get('list') != lst['name']:
                        changes.append(f"MOVED *{card['name']}* from {known[cid].get('list')} → {lst['name']}")
                    elif known[cid].get('dueComplete') != card.get('dueComplete', False):
                        if card.get('dueComplete'):
                            changes.append(f"COMPLETED: {card['name']}")
                        else:
                            changes.append(f"REOPENED: {card['name']}")

            # Check for deleted cards
            for cid, info in known.items():
                if cid not in current_cards:
                    changes.append(f"REMOVED: {info.get('name', 'unknown')}")

            # Save state
            trello_state['known_cards'] = current_cards
            trello_state['last_check'] = int(time.time())
            with open(trello_state_file, 'w') as f:
                json.dump(trello_state, f)

            if changes:
                trello_out = '## 📋 Trello Board Changes\n\n'
                trello_out += '\n'.join(f'- {c}' for c in changes)
                # Also include current board snapshot
                trello_out += '\n\n### Current Board:\n'
                for lst in lists:
                    cards = lst.get('cards', [])
                    open_cards = [c for c in cards if not c.get('dueComplete')]
                    if open_cards:
                        trello_out += f'\n**{lst["name"]}**:\n'
                        for card in open_cards:
                            trello_out += f'- {card["name"]}\n'
                results.append(('TRELLO', trello_out))
        # Auto-update date card (temporal anchor)
        try:
            from datetime import datetime
            today_str = datetime.now().strftime('%A, %B %d, %Y')
            date_card_id = '69e5386452efe00168682d3f'
            expected_name = f'📅 Today: {today_str}'
            current_name = current_cards.get(date_card_id, {}).get('name', '')
            if current_name != expected_name:
                requests.put(
                    f'https://api.trello.com/1/cards/{date_card_id}',
                    params={'key': api_key, 'token': token,
                            'name': expected_name, 'pos': 'top'},
                    timeout=10
                )
        except Exception:
            pass

except Exception as e:
    # Don't let Trello errors break the whole poll
    pass

# 5. Teams gap check (catches what check_inbound misses)
# Run with --minutes 5 --enriched to catch recent gaps with real content
try:
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "teams_tracker/check_gaps.py"), "--minutes", "5", "--enriched"],
        capture_output=True, text=True, timeout=30,
    )
    gap_out = r.stdout.strip() if r.stdout else None
except Exception:
    gap_out = None
if gap_out and gap_out.startswith("TEAMS_GAPS_FOUND"):
    # Only add if we didn't already get Teams output
    if not teams_out:
        results.append(("TEAMS", gap_out))
    else:
        # Append gap info to existing Teams output
        for i, (tag, content) in enumerate(results):
            if tag == "TEAMS":
                results[i] = ("TEAMS", content + "\n\n" + gap_out)
                break

# 6. Teams service health (lightweight)
try:
    r = subprocess.run(
        ["systemctl", "--user", "is-active", "teams-poller"],
        capture_output=True, text=True, timeout=5,
    )
    svc_status = r.stdout.strip()
    if svc_status not in ("active",):
        results.append(("WATCHDOG", f"teams-poller service is {svc_status} — restart needed"))
except Exception:
    pass

# Output only if something needs attention
if results:
    for tag, content in results:
        print(f"=== {tag} ===")
        print(content)
        print()
else:
    # Nothing to do — no output means cron can skip the LLM turn
    pass
