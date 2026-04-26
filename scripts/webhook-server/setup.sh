#!/bin/bash
# Setup MS Graph Webhook Server with Tailscale Funnel
#
# Prerequisites:
#   1. Tailscale Funnel enabled on your tailnet
#   2. MS Graph token with Chat.Read and Mail.Read scopes
#
# Usage: bash setup.sh

set -e

TAILSCALE="/mnt/c/Program Files/Tailscale/tailscale.exe"
PORT=8443

echo "=== MS Graph Webhook Server Setup ==="
echo ""

# Step 1: Get Tailscale hostname
HOSTNAME=$("$TAILSCALE" status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Self']['DNSName'].rstrip('.'))" 2>/dev/null)
if [ -z "$HOSTNAME" ]; then
    echo "ERROR: Could not get Tailscale hostname. Is Tailscale running?"
    exit 1
fi
echo "Tailscale hostname: $HOSTNAME"
WEBHOOK_URL="https://${HOSTNAME}/webhook"
echo "Webhook URL: $WEBHOOK_URL"
echo ""

# Step 2: Set up Tailscale Funnel
echo "Setting up Tailscale Funnel on port $PORT..."
"$TAILSCALE" funnel $PORT &
sleep 3
echo ""

# Step 3: Enable and start webhook server
echo "Enabling webhook server service..."
systemctl --user daemon-reload
systemctl --user enable webhook-server
systemctl --user start webhook-server
sleep 2
systemctl --user status webhook-server --no-pager
echo ""

# Step 4: Test health endpoint
echo "Testing health endpoint..."
curl -sf http://localhost:$PORT/health && echo "" || echo "WARNING: Health check failed"
echo ""

# Step 5: Create Graph subscriptions
echo "Creating Graph webhook subscriptions..."
python3 "$(dirname "$0")/subscriptions.py" create --url "$WEBHOOK_URL"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Webhook server running on port $PORT"
echo "Funnel: $WEBHOOK_URL"
echo ""
echo "Add cron job for subscription renewal (Teams subs expire in 60 min):"
echo "  openclaw cron add --name webhook-renew --every 45m -- python3 $(dirname "$0")/subscriptions.py renew"
