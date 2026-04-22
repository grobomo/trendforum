#!/usr/bin/env python3
"""Slack history scan state manager.

Tracks last-seen message timestamps per channel so the LLM knows
which channels have been checked recently.

Usage:
    # Check if scan is due (outputs JSON if due, nothing if not):
    python3 state_manager.py check
    
    # Update last-seen timestamp for a channel:
    python3 state_manager.py update <channel_id> <timestamp>
    
    # Show current state:
    python3 state_manager.py show
"""

import json
import sys
import time
from pathlib import Path

STATE_FILE = Path.home() / '.openclaw' / 'slack-poller' / 'state.json'
SCAN_INTERVAL = 900  # 15 minutes between full scans

MONITORED_CHANNELS = {
    'C0ATFDQRGRL': '#all-misfits',
    'C0ATJE19YRY': '#coco-chat',
    'C0ATB4AS9PD': '#social',
    'C0ATCRVSB71': '#coco-metacognition',
    'C0ATM9PB59T': '#cdt-imsva-analyzer',
    'C0ATJVC4LUB': '#son',
    'C0ATK8YJQD9': '#scheduling',
}

BOT_IDS = ['U0ATFQQ4WNS', 'U0AURHRR4M6']


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'channels': {}, 'last_scan': 0}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def cmd_check():
    state = load_state()
    last_scan = state.get('last_scan', 0)
    elapsed = int(time.time()) - last_scan
    
    if elapsed < SCAN_INTERVAL:
        # Not due yet
        return
    
    # Output channels that need checking
    result = {
        'scan_due': True,
        'last_scan_ago_min': round(elapsed / 60, 1),
        'channels': {},
        'bot_ids': BOT_IDS,
    }
    for cid, name in MONITORED_CHANNELS.items():
        ch_state = state.get('channels', {}).get(cid, {})
        result['channels'][cid] = {
            'name': name,
            'last_ts': ch_state.get('last_ts', '0'),
        }
    
    print(json.dumps(result))


def cmd_update(channel_id, timestamp):
    state = load_state()
    if 'channels' not in state:
        state['channels'] = {}
    state['channels'][channel_id] = {
        'last_ts': timestamp,
        'last_checked': int(time.time()),
    }
    save_state(state)
    print(f"Updated {channel_id} → {timestamp}")


def cmd_done():
    """Mark scan as complete (update last_scan timestamp)."""
    state = load_state()
    state['last_scan'] = int(time.time())
    save_state(state)
    print("Scan marked complete")


def cmd_show():
    state = load_state()
    last_scan = state.get('last_scan', 0)
    elapsed = int(time.time()) - last_scan if last_scan else None
    print(f"Last scan: {elapsed}s ago" if elapsed else "Never scanned")
    for cid, info in state.get('channels', {}).items():
        name = MONITORED_CHANNELS.get(cid, cid)
        print(f"  {name}: last_ts={info.get('last_ts', '?')}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: state_manager.py [check|update|done|show]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == 'check':
        cmd_check()
    elif cmd == 'update' and len(sys.argv) >= 4:
        cmd_update(sys.argv[2], sys.argv[3])
    elif cmd == 'done':
        cmd_done()
    elif cmd == 'show':
        cmd_show()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
