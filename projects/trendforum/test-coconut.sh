#!/bin/bash
cd "$(dirname "$0")"

# Start server in a subshell so SIGTERM doesn't propagate
pkill -f "tsx src/server" 2>/dev/null || true
COCONUT_POLL_MS=5000 npx tsx src/server/index.ts > /tmp/tf-test.log 2>&1 &
SERVER_PID=$!

cleanup() { kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null; exit 0; }
trap cleanup EXIT

# Wait for server
for i in 1 2 3 4 5 6; do
  curl -sf http://localhost:3847/api/coconut/status >/dev/null 2>&1 && break
  sleep 1
done

PASS=0
FAIL=0

check() {
  if [ "$1" = "true" ]; then
    echo "  PASS: $2"
    PASS=$((PASS+1))
  else
    echo "  FAIL: $2"
    FAIL=$((FAIL+1))
  fi
}

echo "=== 1. Status (stopped) ==="
STATUS=$(curl -s http://localhost:3847/api/coconut/status)
echo "  $STATUS"
RUNNING=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['running'])" 2>/dev/null)
check "$([ "$RUNNING" = "False" ] && echo true)" "Bot initially stopped"

echo "=== 2. Admin login ==="
ADMIN_TOKEN=$(curl -s http://localhost:3847/api/auth/admin \
  -H "Content-Type: application/json" \
  -d '{"password":"admin2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "$([ -n "$ADMIN_TOKEN" ] && echo true)" "Admin token received"

echo "=== 3. Start coconut ==="
START=$(curl -s -X POST http://localhost:3847/api/coconut/start \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "  $START"
RUNNING=$(echo "$START" | python3 -c "import sys,json; print(json.load(sys.stdin)['running'])" 2>/dev/null)
check "$([ "$RUNNING" = "True" ] && echo true)" "Bot started"

echo "=== 4. User login ==="
USER_TOKEN=$(curl -s http://localhost:3847/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"password":"demo2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "$([ -n "$USER_TOKEN" ] && echo true)" "User token received"

echo "=== 5. Create post ==="
POST_RESULT=$(curl -s -X POST http://localhost:3847/api/posts \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subforumId":1,"title":"Coconut E2E Test","body":"Testing the bot!"}')
echo "  $POST_RESULT"
POST_ID=$(echo "$POST_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
check "$([ -n "$POST_ID" ] && [ "$POST_ID" != "0" ] && echo true)" "Post created (id=$POST_ID)"

echo "=== 6. Wait 8s for poll ==="
sleep 8

echo "=== 7. Check comments (via GET /api/posts/:id) ==="
POST_DATA=$(curl -s "http://localhost:3847/api/posts/$POST_ID")
echo "$POST_DATA" | python3 -c "
import sys,json
post = json.load(sys.stdin)
comments = post.get('comments', [])
coconut = [c for c in comments if c.get('displayName') == 'Coconut']
print(f'  Coconut replies: {len(coconut)}')
if coconut:
    print('  PASS: Coconut replied!')
    for c in coconut:
        print(f'    -> {c[\"body\"]}')
else:
    print('  NOTE: Coconut did not reply (60% chance per post, may need retry)')
" 2>/dev/null

echo "=== 8. Stop coconut ==="
STOP=$(curl -s -X POST http://localhost:3847/api/coconut/stop \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "  $STOP"
RUNNING=$(echo "$STOP" | python3 -c "import sys,json; print(json.load(sys.stdin)['running'])" 2>/dev/null)
check "$([ "$RUNNING" = "False" ] && echo true)" "Bot stopped"

echo "=== 9. Non-admin start (expect 403) ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3847/api/coconut/start \
  -H "Authorization: Bearer $USER_TOKEN")
echo "  HTTP $HTTP_CODE"
check "$([ "$HTTP_CODE" = "403" ] && echo true)" "Admin guard blocks non-admin"

echo ""
echo "=== Server logs ==="
cat /tmp/tf-test.log 2>/dev/null

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
