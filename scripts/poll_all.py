#!/usr/bin/env python3
"""Unified poller — runs all checks in one pass.

Runs Teams inbound check, GitHub poll, and email poll.
Only produces output if something needs attention.
Also checks Teams service health.

Usage:
    python3 poll_all.py
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
results = []


def run_script(name, script_path):
    """Run a poller script and capture output."""
    try:
        r = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=20,
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
if email_out:
    results.append(("EMAIL", email_out))

# 4. Teams service health (lightweight)
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
