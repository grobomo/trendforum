#!/usr/bin/env python3
"""Post GitHub replies from OpenClaw's structured output.

Usage:
    echo "<reply text with GITHUB_REPLY blocks>" | python3 send_reply.py
    python3 send_reply.py "<reply text>"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poll_github import post_replies, load_config


def main():
    if len(sys.argv) > 1:
        reply_text = " ".join(sys.argv[1:])
    else:
        reply_text = sys.stdin.read().strip()

    if not reply_text:
        print("No reply text provided", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    posted = post_replies(reply_text, config)
    print(f"Posted {posted} GitHub comment(s)")


if __name__ == "__main__":
    main()
