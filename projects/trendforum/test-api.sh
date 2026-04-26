#!/bin/bash
cd "$(dirname "$0")"

npx tsx src/server/index.ts &
SERVER_PID=$!
sleep 3

cleanup() { kill $SERVER_PID 2>/dev/null; }
trap cleanup EXIT

BASE="http://localhost:3847/api"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo "PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc (expected '$expected', got '${actual:0:80}')"
    FAIL=$((FAIL+1))
  fi
}

authed() {
  curl -s "$@" -H "Authorization: Bearer $TOKEN"
}

# 1. Auth
AUTH_RESP=$(curl -s -X POST "$BASE/auth/verify" -H "Content-Type: application/json" -d '{"password":"demo2026"}')
TOKEN=$(echo "$AUTH_RESP" | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)
check "Auth returns JWT" "eyJ" "$TOKEN"

# 2. Subforums
SF_RESP=$(authed "$BASE/subforums")
SF_COUNT=$(echo "$SF_RESP" | grep -o '"slug"' | wc -l)
check "8 subforums seeded" "8" "$SF_COUNT"
check "Has security-research" "security-research" "$SF_RESP"
check "Has watercooler" "watercooler" "$SF_RESP"
check "Has product-feedback" "product-feedback" "$SF_RESP"

# 3. Posts feed
POSTS_RESP=$(authed "$BASE/posts?sort=new")
check "Posts feed has Welcome post" "Welcome to TrendForum" "$POSTS_RESP"
check "Posts feed has music post" "listening to right now" "$POSTS_RESP"

# 4. Single post
POST_RESP=$(authed "$BASE/posts/1")
check "Get post by ID" "Welcome to TrendForum" "$POST_RESP"

# 5. Subforum posts
SF_POSTS=$(authed "$BASE/subforums/general/posts")
check "Subforum posts" "Welcome" "$SF_POSTS"

# 6. Comment
CMT_RESP=$(authed -X POST "$BASE/posts/1/comments" -H "Content-Type: application/json" -d '{"body":"E2E test comment"}')
check "Create comment" "displayName" "$CMT_RESP"

# 7. Vote
VOTE_RESP=$(authed -X POST "$BASE/vote" -H "Content-Type: application/json" -d '{"postId":1,"value":1}')
check "Vote on post" "voted" "$VOTE_RESP"

# 8. Report
RPT_RESP=$(authed -X POST "$BASE/report" -H "Content-Type: application/json" -d '{"postId":1,"reason":"test"}')
check "Report content" "id" "$RPT_RESP"

# 9. Feed
FEED_RESP=$(authed "$BASE/feed?since=2020-01-01T00:00:00Z")
check "Feed endpoint" "posts" "$FEED_RESP"

# 10. Search
SEARCH_RESP=$(authed "$BASE/search?q=Welcome")
check "Search" "Welcome" "$SEARCH_RESP"

# 11. Bad password
BAD=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/verify" -H "Content-Type: application/json" -d '{"password":"wrong"}')
check "Reject bad password" "401" "$BAD"

echo ""
echo "Results: $PASS/$((PASS+FAIL)) passed"
