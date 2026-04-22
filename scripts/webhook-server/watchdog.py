#!/usr/bin/env python3
"""
Webhook/Poller Failover Watchdog

Monitors webhook health and manages the poller as a fallback:
- When webhooks are healthy: stop the teams-poller systemd service
- When webhooks are unresponsive for >30s: restart poller automatically
- When webhook subscriptions lapse: auto-renew them

Run via cron every 1 minute:
    * * * * * python3 /home/ubu/.openclaw/workspace/scripts/webhook-server/watchdog.py

State file: ~/.openclaw/webhook-server/watchdog-state.json
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [watchdog] %(message)s",
)
log = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".openclaw" / "webhook-server"
STATE_FILE = STATE_DIR / "watchdog-state.json"
SUBSCRIPTIONS_FILE = STATE_DIR / "subscriptions.json"
WEBHOOK_SERVER_PORT = 8445
SUBSCRIPTIONS_SCRIPT = Path.home() / ".openclaw" / "workspace" / "scripts" / "webhook-server" / "subscriptions.py"
POLLER_SERVICE = "teams-poller"

# Thresholds
WEBHOOK_UNHEALTHY_THRESHOLD = 30  # seconds before declaring webhooks unhealthy
SUBSCRIPTION_RENEWAL_BUFFER = 600  # renew subscriptions 10 min before expiry
MAX_HEALTH_CHECK_TIMEOUT = 5  # seconds to wait for health check response


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "mode": "unknown",  # "webhook" | "poller" | "unknown"
            "webhook_last_healthy": 0,
            "webhook_last_unhealthy": 0,
            "poller_stopped_at": 0,
            "poller_started_at": 0,
            "last_subscription_check": 0,
            "failover_count": 0,
            "last_run": 0,
        }


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_webhook_health() -> bool:
    """Check if webhook server is responding."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             f"http://127.0.0.1:{WEBHOOK_SERVER_PORT}/health",
             "--max-time", str(MAX_HEALTH_CHECK_TIMEOUT)],
            capture_output=True, text=True, timeout=MAX_HEALTH_CHECK_TIMEOUT + 2,
        )
        return result.stdout.strip() == "200"
    except Exception:
        return False


def _load_subscriptions() -> list:
    """Load subscriptions from state file. Handles both list and dict formats."""
    try:
        with open(SUBSCRIPTIONS_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    # Handle dict with 'subscriptions' key or raw list
    if isinstance(data, dict):
        return data.get("subscriptions", [])
    if isinstance(data, list):
        return data
    return []


def _parse_expiration(sub: dict) -> float:
    """Parse expiration field to epoch. Handles ISO 8601 strings and epoch floats."""
    exp = sub.get("expiration") or sub.get("expires_epoch", 0)
    if isinstance(exp, (int, float)):
        return float(exp)
    if isinstance(exp, str):
        try:
            from datetime import datetime as dt
            # Parse ISO format
            return dt.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
    return 0


def check_subscriptions_valid() -> bool:
    """Check if webhook subscriptions exist and haven't expired."""
    subs = _load_subscriptions()
    if not subs:
        return False

    now = time.time()
    for sub in subs:
        expires = _parse_expiration(sub)
        if expires > now:
            return True
    return False


def check_subscriptions_expiring_soon() -> bool:
    """Check if subscriptions are within renewal buffer of expiry."""
    subs = _load_subscriptions()
    if not subs:
        return True  # No subs = definitely needs renewal

    now = time.time()
    for sub in subs:
        expires = _parse_expiration(sub)
        if 0 < expires - now < SUBSCRIPTION_RENEWAL_BUFFER:
            return True
    return False


def get_poller_status() -> str:
    """Check if teams-poller systemd service is running."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", POLLER_SERVICE],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()  # "active", "inactive", "failed"
    except Exception:
        return "unknown"


def stop_poller():
    """Stop the teams-poller service."""
    log.info("Stopping teams-poller (webhooks healthy)")
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", POLLER_SERVICE],
            capture_output=True, timeout=10,
        )
    except Exception as e:
        log.warning("Failed to stop poller: %s", e)


def start_poller():
    """Start/restart the teams-poller service."""
    log.info("Starting teams-poller (webhook failover)")
    try:
        subprocess.run(
            ["systemctl", "--user", "restart", POLLER_SERVICE],
            capture_output=True, timeout=10,
        )
    except Exception as e:
        log.warning("Failed to start poller: %s", e)


def renew_subscriptions():
    """Re-register webhook subscriptions."""
    log.info("Renewing webhook subscriptions")
    try:
        result = subprocess.run(
            [sys.executable, str(SUBSCRIPTIONS_SCRIPT), "register"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            log.info("Subscriptions renewed successfully")
        else:
            log.warning("Subscription renewal failed: %s", result.stderr[:200])
    except Exception as e:
        log.warning("Subscription renewal error: %s", e)


def run_watchdog():
    """Main watchdog logic — runs once per invocation (called by cron)."""
    state = load_state()
    now = time.time()
    state["last_run"] = now

    webhook_healthy = check_webhook_health()
    subs_valid = check_subscriptions_valid()
    poller_status = get_poller_status()

    log.info("Health: webhook=%s subs=%s poller=%s mode=%s",
             "UP" if webhook_healthy else "DOWN",
             "VALID" if subs_valid else "EXPIRED",
             poller_status, state["mode"])

    # ── Case 1: Webhooks healthy + subscriptions valid → stop poller ──
    if webhook_healthy and subs_valid:
        state["webhook_last_healthy"] = now
        state["mode"] = "webhook"

        if poller_status == "active":
            stop_poller()
            state["poller_stopped_at"] = now
            log.info("Switched to webhook-primary mode, poller stopped")

    # ── Case 2: Webhooks unhealthy → failover to poller ──
    elif not webhook_healthy:
        state["webhook_last_unhealthy"] = now

        # Only failover if unhealthy for longer than threshold
        time_since_healthy = now - state.get("webhook_last_healthy", 0)
        if time_since_healthy > WEBHOOK_UNHEALTHY_THRESHOLD:
            if poller_status != "active":
                start_poller()
                state["poller_started_at"] = now
                state["failover_count"] = state.get("failover_count", 0) + 1
                state["mode"] = "poller"
                log.warning("FAILOVER: webhooks unhealthy for %.0fs, poller activated", time_since_healthy)

    # ── Case 3: Webhooks healthy but subs expired → renew + start poller as safety ──
    elif webhook_healthy and not subs_valid:
        renew_subscriptions()
        state["last_subscription_check"] = now
        # Keep poller running until subs confirmed valid
        if poller_status != "active":
            start_poller()
            state["mode"] = "poller"

    # ── Proactive subscription renewal ──
    if check_subscriptions_expiring_soon():
        if now - state.get("last_subscription_check", 0) > 300:  # Don't renew more than every 5 min
            renew_subscriptions()
            state["last_subscription_check"] = now

    save_state(state)

    # Print summary for cron log
    print(json.dumps({
        "mode": state["mode"],
        "webhook": "UP" if webhook_healthy else "DOWN",
        "subs": "VALID" if subs_valid else "EXPIRED",
        "poller": poller_status,
        "failovers": state.get("failover_count", 0),
    }))


if __name__ == "__main__":
    run_watchdog()
