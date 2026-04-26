#!/bin/bash
cd "$(dirname "$0")"
RESULTS=/tmp/tf-upload-results.txt
> "$RESULTS"

pkill -f "tsx src/server" 2>/dev/null || true
npx tsx src/server/index.ts > /tmp/tf-img.log 2>&1 &
SERVER_PID=$!

for i in 1 2 3 4 5 6; do
  curl -sf http://localhost:3847/api/coconut/status >/dev/null 2>&1 && break
  sleep 1
done

TOKEN=$(curl -s http://localhost:3847/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"password":"trender2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Create test image
echo -n "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test.png

# Upload
UPLOAD=$(curl -s -X POST http://localhost:3847/api/upload \
  -H "Authorization: Bearer $TOKEN" -F "image=@/tmp/test.png")
IMG_URL=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('url','FAIL'))" 2>/dev/null)
echo "1. Upload: $IMG_URL" >> "$RESULTS"

# Create post with image
POST=$(curl -s -X POST http://localhost:3847/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"subforumId\":1,\"title\":\"Image Test\",\"imageUrl\":\"$IMG_URL\"}")
POST_ID=$(echo "$POST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',0))" 2>/dev/null)
echo "2. Post created: id=$POST_ID" >> "$RESULTS"

# Fetch image
IMG_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3847$IMG_URL")
echo "3. Image fetch: HTTP $IMG_HTTP (expect 200)" >> "$RESULTS"

# Verify post has imageUrl
POST_IMG=$(curl -s "http://localhost:3847/api/posts/$POST_ID" | python3 -c "import sys,json; p=json.load(sys.stdin); print('PASS' if p.get('imageUrl') else 'FAIL')" 2>/dev/null)
echo "4. Post imageUrl: $POST_IMG" >> "$RESULTS"

# No-auth upload
NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3847/api/upload -F "image=@/tmp/test.png")
echo "5. No-auth upload: HTTP $NO_AUTH (expect 401)" >> "$RESULTS"

kill $SERVER_PID 2>/dev/null
cat "$RESULTS"
