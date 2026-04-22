#!/usr/bin/env python3
"""MS Graph Webhook Server for OpenClaw.

Receives change notifications from Microsoft Graph for:
- Teams chat messages
- Email inbox changes

On notification, wakes OpenClaw via /v1/chat/completions to process the event.

Usage:
    python3 server.py                    # Run on port 8443
    python3 server.py --port 9000        # Custom port
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [webhook-server] %(message)s",
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
OPENCLAW_PORT = 18789
POLL_SCRIPT = Path.home() / ".openclaw" / "workspace" / "scripts" / "poll_all.py"
QUEUE_REPLY_SCRIPT = Path.home() / ".openclaw" / "workspace" / "scripts" / "teams-poller" / "queue_reply.py"

# Debounce: don't wake OpenClaw more than once per N seconds per resource type
WAKE_DEBOUNCE_SECONDS = 15
_last_wake = {"teams": 0, "email": 0, "trello": 0}
_gateway_token = None


def _get_gateway_token() -> str | None:
    """Read gateway auth token from openclaw.json (cached)."""
    global _gateway_token
    if _gateway_token:
        return _gateway_token
    try:
        with open(OPENCLAW_CONFIG) as f:
            cfg = json.load(f)
        _gateway_token = cfg.get("gateway", {}).get("auth", {}).get("token")
        return _gateway_token
    except Exception:
        return None


def wake_openclaw(resource_type: str):
    """Wake OpenClaw to process new messages/emails. Debounced per resource type."""
    now = time.time()
    if now - _last_wake.get(resource_type, 0) < WAKE_DEBOUNCE_SECONDS:
        log.debug("Wake debounced for %s (%.0fs since last)", resource_type, now - _last_wake[resource_type])
        return
    _last_wake[resource_type] = now

    token = _get_gateway_token()
    if not token:
        log.warning("No gateway token, skipping wake")
        return

    def _do_wake():
        try:
            if resource_type == "teams":
                prompt = "New Teams message received via webhook. Run python3 /home/ubu/.openclaw/workspace/scripts/teams_tracker/check_gaps.py --minutes 1 --enriched and handle output: if TEAMS_GAPS_FOUND, compose and send replies for read-write chats via queue_reply.py, then mark responded with tracker.py respond --chat-id <id>. For read-only chats, flag important items to Joel via Slack DM. If no output, do nothing."
            elif resource_type == "email":
                prompt = "New email received via webhook. Run python3 /home/ubu/.openclaw/workspace/scripts/poll_all.py and handle output: EMAIL = summarize and flag urgent items. If no output, do nothing."
            elif resource_type == "trello":
                prompt = "Trello board updated via webhook. Run python3 /home/ubu/.openclaw/workspace/scripts/schedule-briefing/gather.py --source trello_todo,trello_companies and review changes. If relevant to schedule or pending tasks, post update to #scheduling (C0ATK8YJQD9). Check if any card was assigned, moved, or has a due date change."
            else:
                prompt = f"Webhook notification for {resource_type}. Run python3 /home/ubu/.openclaw/workspace/scripts/poll_all.py and handle any output."

            payload = json.dumps({
                "model": "openclaw/main",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Process {resource_type} webhook notification now."},
                ],
                "stream": False,
            })
            subprocess.run(
                ["curl", "-s", "-X", "POST",
                 f"http://127.0.0.1:{OPENCLAW_PORT}/v1/chat/completions",
                 "-H", f"Authorization: Bearer {token}",
                 "-H", "Content-Type: application/json",
                 "-d", payload,
                 "--max-time", "120"],
                capture_output=True, timeout=130,
            )
            log.info("OpenClaw wake completed for %s", resource_type)
        except Exception as e:
            log.warning("Failed to wake OpenClaw for %s: %s", resource_type, e)

    t = threading.Thread(target=_do_wake, daemon=True)
    t.start()
    log.info("Sent wake to OpenClaw for %s (background thread)", resource_type)


# ── Central Tracker Integration ──────────────────────────────────

import re

# Use the central teams-tracker (shared by webhook, poller, queue_reply, Graph API)
_TRACKER_DIR = Path.home() / ".openclaw" / "workspace" / "scripts"
if str(_TRACKER_DIR) not in sys.path:
    sys.path.insert(0, str(_TRACKER_DIR))

try:
    from teams_tracker.tracker import TeamsTracker
    _webhook_tracker = TeamsTracker()
except ImportError:
    _webhook_tracker = None
    log.warning("teams_tracker not found — webhook tracking disabled")

def _record_pending(resource: str, change_type: str):
    """Extract chat_id and msg_id from Graph resource path and record in tracker.
    
    Resource format: chats('19:xxx@thread.v2')/messages('1234567890')
    Only records on 'created' (new messages), not 'updated' (edits/reactions).
    """
    if change_type != "created":
        return
    
    # Extract IDs from resource path
    m = re.search(r"chats\('([^']+)'\)/messages\('([^']+)'\)", resource)
    if not m:
        return
    
    chat_id, msg_id = m.group(1), m.group(2)
    
    if _webhook_tracker:
        try:
            _webhook_tracker.record_message(
                chat_id=chat_id, msg_id=msg_id,
                sender="unknown", source="webhook",
            )
        except Exception as e:
            log.warning("Failed to record in central tracker: %s", e)
    else:
        log.debug("Tracker unavailable, skipping record for %s", msg_id)


# ── HTTP Handler ─────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    """Handles MS Graph webhook notifications."""

    def do_POST(self):
        """Handle incoming Graph change notifications."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else ""

        # Check for validation token in query string (subscription validation)
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        validation_token = params.get("validationToken", [None])[0]

        if validation_token:
            # Subscription validation — respond with the token as plain text
            log.info("Subscription validation request received")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(validation_token.encode("utf-8"))
            return

        # Parse notification payload
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            log.warning("Invalid JSON in webhook body")
            self.send_response(400)
            self.end_headers()
            return

        # Respond 202 immediately (Graph requires fast response)
        self.send_response(202)
        self.end_headers()

        # Process notifications
        notifications = data.get("value", [])
        if not notifications:
            log.debug("Empty notification payload")
            return

        for notification in notifications:
            resource = notification.get("resource", "")
            change_type = notification.get("changeType", "")
            subscription_id = notification.get("subscriptionId", "")

            log.info("Notification: resource=%s changeType=%s sub=%s",
                     resource, change_type, subscription_id[:12])

            # Determine resource type and wake OpenClaw
            if "chats" in resource and "messages" in resource:
                # Extract chat_id and msg_id for response tracking
                _record_pending(resource, change_type)
                wake_openclaw("teams")
            elif "messages" in resource and "chats" not in resource:
                # Mail messages
                wake_openclaw("email")
            else:
                log.info("Unknown resource type: %s", resource)

        # ── Trello webhook ───────────────────────────────────
        if self.path.startswith("/trello"):
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                log.warning("Invalid JSON in Trello webhook body")
                self.send_response(400)
                self.end_headers()
                return

            self.send_response(200)
            self.end_headers()

            action = data.get("action", {})
            action_type = action.get("type", "unknown")
            board_name = data.get("model", {}).get("name", "?")
            card_name = action.get("data", {}).get("card", {}).get("name", "")
            list_name = action.get("data", {}).get("list", {}).get("name", "")
            member = action.get("memberCreator", {}).get("fullName", "?")

            log.info("Trello: %s on '%s' by %s (board: %s, list: %s)",
                     action_type, card_name or board_name, member, board_name, list_name)

            wake_openclaw("trello")
            return

    def do_HEAD(self):
        """Handle Trello webhook validation (HEAD request)."""
        if self.path.startswith("/trello"):
            log.info("Trello webhook HEAD validation")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_wake": _last_wake,
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default HTTP request logging (we have our own)."""
        pass


# ── Main ─────────────────────────────────────────────────────────

def run_server(port: int = 8443):
    """Start the webhook server."""
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    log.info("Webhook server starting on port %d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook server shutting down")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="MS Graph Webhook Server")
    parser.add_argument("--port", type=int, default=8443, help="Listen port (default: 8443)")
    args = parser.parse_args()
    run_server(args.port)


if __name__ == "__main__":
    main()
