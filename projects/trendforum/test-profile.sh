#!/bin/bash
cd "$(dirname "$0")"
PASS=0; FAIL=0
check() { if [ "$1" = "true" ]; then echo "  PASS: $2"; PASS=$((PASS+1)); else echo "  FAIL: $2"; FAIL=$((FAIL+1)); fi; }

pkill -f "tsx src/server" 2>/dev/null || true
npx tsx src/server/index.ts > /tmp/tf-profile.log 2>&1 &
SERVER_PID=$!
cleanup() { kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null; }
trap cleanup EXIT

for i in 1 2 3 4 5 6; do
  curl -sf http://localhost:3847/api/coconut/status >/dev/null 2>&1 && break
  sleep 1
done

echo "=== 1. Get member token ==="
TOKEN=$(curl -s http://localhost:3847/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"password":"demo2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "$([ -n "$TOKEN" ] && echo true)" "Member token received"

echo "=== 2. Register pseudonym ==="
REG=$(curl -s http://localhost:3847/api/profile/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pseudonym":"TestUser","password":"secret123"}')
PTOKEN=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "$([ -n "$PTOKEN" ] && echo true)" "Profile registered"

echo "=== 3. Profile /me ==="
PSEUDO=$(curl -s http://localhost:3847/api/profile/me \
  -H "Authorization: Bearer $PTOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['profile']['pseudonym'])" 2>/dev/null)
check "$([ "$PSEUDO" = "TestUser" ] && echo true)" "Profile me returns TestUser"

echo "=== 4. Post as profile ==="
POST=$(curl -s -X POST http://localhost:3847/api/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PTOKEN" \
  -d '{"subforumId":1,"title":"Profile Test Post","body":"Posted by TestUser"}')
PID=$(echo "$POST" | python3 -c "import sys,json; p=json.load(sys.stdin); print(p.get('profileId',''))" 2>/dev/null)
POST_ID=$(echo "$POST" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
check "$([ -n "$PID" ] && [ "$PID" != "None" ] && [ "$PID" != "" ] && echo true)" "Post linked to profile (id=$PID)"

echo "=== 5. Comment shows pseudonym ==="
COMMENT=$(curl -s -X POST http://localhost:3847/api/posts/$POST_ID/comments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PTOKEN" \
  -d '{"body":"A test comment"}')
DNAME=$(echo "$COMMENT" | python3 -c "import sys,json; print(json.load(sys.stdin)['displayName'])" 2>/dev/null)
check "$([ "$DNAME" = "TestUser" ] && echo true)" "Display name is pseudonym ($DNAME)"

echo "=== 6. Public profile page ==="
PCOUNT=$(curl -s http://localhost:3847/api/profile/TestUser | python3 -c "import sys,json; print(json.load(sys.stdin)['profile']['_count']['posts'])" 2>/dev/null)
check "$([ "$PCOUNT" = "1" ] && echo true)" "Profile page shows 1 post"

echo "=== 7. Duplicate pseudonym blocked ==="
DUP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3847/api/profile/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pseudonym":"TestUser","password":"other123"}')
check "$([ "$DUP" = "409" ] && echo true)" "Duplicate blocked (HTTP $DUP)"

echo "=== 8. Profile login ==="
LTOKEN=$(curl -s http://localhost:3847/api/profile/login \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pseudonym":"TestUser","password":"secret123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "$([ -n "$LTOKEN" ] && echo true)" "Profile login works"

echo "=== 9. Reserved name blocked ==="
RES=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3847/api/profile/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pseudonym":"admin","password":"test1234"}')
check "$([ "$RES" = "400" ] && echo true)" "Reserved name blocked (HTTP $RES)"

echo "=== 10. Pagination ==="
COUNT=$(curl -s 'http://localhost:3847/api/posts?page=1&sort=new' | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
check "$([ -n "$COUNT" ] && [ "$COUNT" -ge 0 ] 2>/dev/null && echo true)" "Pagination page 1 returns $COUNT posts"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
