#!/usr/bin/env python3
"""Wrapper: run monitor-claude-project.py and post summary to Slack DM.

Uses Slack Bot Token from OpenClaw config to post directly.
"""
import json
import subprocess
import sys
import os
from pathlib import Path

SUMMARY_FILE = "/tmp/claude-monitor-summary.txt"
SLACK_DM = "D0ATWPM4DTK"


def get_slack_token():
    """Get Slack bot token from environment (set by OpenClaw systemd service)."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if token:
        return token
    # Fallback: try OpenClaw config
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        slack = config.get("channels", {}).get("slack", {})
        bt = slack.get("botToken", "")
        if bt.startswith("${"): return None  # env var ref, not resolved
        return bt or None
    except Exception:
        return None


def post_to_slack(token, channel, text):
    """Post message to Slack via API."""
    import urllib.request
    data = json.dumps({"channel": channel, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"Slack post failed: {e}", file=sys.stderr)
        return False


def main():
    # Clean up any old summary
    if os.path.exists(SUMMARY_FILE):
        os.unlink(SUMMARY_FILE)

    # Run the monitor
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "monitor-claude-project.py")],
        timeout=30
    )

    # Check if there's a summary to post
    if not os.path.exists(SUMMARY_FILE):
        return  # No activity — silent

    summary = Path(SUMMARY_FILE).read_text().strip()
    if not summary:
        return

    token = get_slack_token()
    if not token:
        print("No Slack token found in OpenClaw config", file=sys.stderr)
        return

    if post_to_slack(token, SLACK_DM, summary):
        print(f"Posted to Slack ({len(summary)} chars)")
    else:
        print("Failed to post to Slack", file=sys.stderr)

    os.unlink(SUMMARY_FILE)


if __name__ == "__main__":
    main()
