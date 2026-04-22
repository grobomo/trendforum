#!/usr/bin/env python3
"""
Auto-detect new Slack channels the bot is a member of and add them
to openclaw.json with requireMention: false.

Run periodically via cron (e.g., every 5 min).
Outputs channel names when new ones are added (for cron log).
Silent when nothing changes.
"""

import json
import keyring
import subprocess
import urllib.request


def get_bot_channels():
    """Get all channels the bot is a member of."""
    token = keyring.get_password('openclaw', 'SLACK_BOT_TOKEN')
    if not token:
        return []

    channels = []
    cursor = None

    while True:
        url = f'https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200&exclude_archived=true'
        if cursor:
            url += f'&cursor={cursor}'

        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        resp = json.loads(urllib.request.urlopen(req).read())

        if not resp.get('ok'):
            break

        for c in resp.get('channels', []):
            if c.get('is_member'):
                channels.append({
                    'id': c['id'],
                    'name': c.get('name', ''),
                })

        cursor = resp.get('response_metadata', {}).get('next_cursor', '')
        if not cursor:
            break

    return channels


def sync_config():
    config_path = '/home/ubu/.openclaw/openclaw.json'

    with open(config_path) as f:
        config = json.load(f)

    slack = config.get('channels', {}).get('slack', {})
    existing = slack.get('channels', {})

    bot_channels = get_bot_channels()
    added = []

    for ch in bot_channels:
        if ch['id'] not in existing:
            existing[ch['id']] = {'requireMention': False}
            added.append(f"#{ch['name']} ({ch['id']})")

    if added:
        slack['channels'] = existing
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Restart gateway to pick up changes
        subprocess.run(
            ['systemctl', '--user', 'restart', 'openclaw-gateway'],
            capture_output=True, timeout=30
        )

        for name in added:
            print(f'Added: {name}')
    # else: silent — nothing to do


if __name__ == '__main__':
    sync_config()
