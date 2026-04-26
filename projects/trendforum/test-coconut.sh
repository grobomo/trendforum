#!/bin/bash
set -e
cd "$(dirname "$0")"

cleanup() { kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null; }

# Start server
pkill -f "tsx src/server" 2>/dev/null || true
COCONUT_POLL_MS=5000 npx tsx src/server/index.ts &
SERVER_PID=$!
trap cleanup EXIT

# Wait for server
for i in 1 2 3 4 5 6; do
  curl -sf http://localhost:3847/api/coconut/status >/dev/null 2>&1 && break
  sleep 1
done

echo "=== Status (stopped) ==="
curl -s http://localhost:3847/api/coconut/status
echo ""

# Login admin
ADMIN_TOKEN=$(curl -s http://localhost:3847/api/auth/admin \
  -H "Content-Type: application/json" \
  -d '{"password":"admin2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Admin token OK"

# Start coconut
echo "=== Start coconut ==="
curl -s -X POST http://localhost:3847/api/coconut/start \
  -H "Authorization: Bearer $ADMIN_TOKEN"
echo ""

# Login user, create post
USER_TOKEN=$(curl -s http://localhost:3847/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"password":"trender2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "User token OK"

echo "=== Create post ==="
POST_RESULT=$(curl -s -X POST http://localhost:3847/api/posts \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subforumId":1,"title":"Coconut E2E Test","body":"Testing the bot!"}')
echo "$POST_RESULT"
POST_ID=$(echo "$POST_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Wait for poll cycle (5s interval + buffer)
echo "Waiting 8s for poll..."
sleep 8

echo "=== Comments on post $POST_ID ==="
COMMENTS=$(curl -s "http://localhost:3847/api/posts/$POST_ID/comments")
echo "$COMMENTS"

# Check if Coconut replied
HAS_COCONUT=$(echo "$COMMENTS" | python3 -c "
import sys,json
comments = json.load(sys.stdin)
coconut = [c for c in comments if c.get('displayName') == 'Coconut']
print(f'Coconut replies: {len(coconut)}')
if coconut:
    print('PASS: Coconut replied!')
    for c in coconut:
        print(f'  -> {c[\"body\"]}')
else:
    print('NOTE: Coconut did not reply (60% chance per post, may need retry)')
")
echo "$HAS_COCONUT"

# Stop
echo "=== Stop coconut ==="
curl -s -X POST http://localhost:3847/api/coconut/stop \
  -H "Authorization: Bearer $ADMIN_TOKEN"
echo ""

# Auth guard test
echo "=== Non-admin start (expect 403) ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3847/api/coconut/start \
  -H "Authorization: Bearer $USER_TOKEN")
echo "HTTP status: $HTTP_CODE"
[ "$HTTP_CODE" = "403" ] && echo "PASS: Admin guard works" || echo "FAIL: Expected 403"

echo "=== DONE ==="
