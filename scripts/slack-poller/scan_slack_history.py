#!/usr/bin/env python3
"""Slack history scanner — checks monitored channels for unread messages.

Reads channel history state from ~/.openclaw/slack-poller/state.json
and outputs any new messages since last check. Designed to be called
from poll_all.py or standalone.

This solves the structural gap: Teams/GitHub/Email are polled, but
Slack relies on native delivery which is lost on session restart/compaction.
"""

import json
import os
import sys
import time
from pathlib import Path

# Channels to monitor (id → name mapping)
MONITORED_CHANNELS = {
    'C0ATFDQRGRL': '#all-misfits',
    'C0ATJE19YRY': '#coco-chat',
    'C0ATB4AS9PD': '#social',
    'C0ATCRVSB71': '#coco-metacognition',
    'C0ATM9PB59T': '#cdt-imsva-analyzer',
    'C0ATJVC4LUB': '#son',
    'C0ATK8YJQD9': '#scheduling',
}

# Bot user IDs to ignore (our own messages)
BOT_IDS = {'U0ATFQQ4WNS', 'U0AURHRR4M6'}  # Coconut, Hermes

STATE_FILE = Path.home() / '.openclaw' / 'slack-poller' / 'state.json'


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'channels': {}, 'last_check': 0}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state['last_check'] = int(time.time())
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    """Output new messages found in monitored Slack channels.
    
    This script is meant to be called by the LLM via poll_all.py.
    It outputs a formatted report of new messages that need attention.
    The LLM reads the output and decides how to respond.
    
    Since we can't call the Slack API directly (token is env-var ref),
    this script just manages state. The actual channel reading is done
    by the LLM using the message(action=read) tool.
    
    Output format: JSON with channels that need checking.
    """
    state = load_state()
    last_check = state.get('last_check', 0)
    
    # If we checked less than 60 seconds ago, skip
    if time.time() - last_check < 60:
        return
    
    # Output which channels need checking and their last-seen timestamps
    channels_to_check = {}
    for cid, name in MONITORED_CHANNELS.items():
        last_ts = state.get('channels', {}).get(cid, {}).get('last_ts', '0')
        channels_to_check[cid] = {
            'name': name,
            'last_ts': last_ts,
        }
    
    # Save state with current check time
    save_state(state)
    
    print(json.dumps({
        'action': 'check_channels',
        'channels': channels_to_check,
        'last_check_ago': int(time.time()) - last_check if last_check else None,
    }))


if __name__ == '__main__':
    main()
