#!/usr/bin/env bash
# Create a new lesson file from structured input
# Usage: create-lesson.sh <number> <slug> <title>
# Reads lesson body from stdin or generates template
# Automatically mirrors to Trello Lessons board Inbox

set -euo pipefail

LESSONS_DIR="$HOME/.openclaw/workspace/memory/lessons"
HOOKS_MONITOR="$HOME/.openclaw/workspace/memory/hooks/hook-monitor.json"

NUM="${1:?Usage: create-lesson.sh <number> <slug> <title>}"
SLUG="${2:?Missing slug}"
TITLE="${3:?Missing title}"

PADDED=$(printf "%03d" "$NUM")
FILENAME="${PADDED}-${SLUG}.md"
FILEPATH="${LESSONS_DIR}/${FILENAME}"

if [[ -f "$FILEPATH" ]]; then
  echo "ERROR: Lesson file already exists: $FILEPATH"
  exit 1
fi

mkdir -p "$LESSONS_DIR"

# Check if content is piped in
if [[ -t 0 ]]; then
  # No stdin — generate template
  cat > "$FILEPATH" << EOF
# Lesson: ${TITLE}

## Observation
[What happened]

## The Lesson
[What to do differently]

## Source
- Session transcript: [path or date]
- Conversation with: [who]
- Date observed: $(date +%Y-%m-%d)

## Hook
- Has hook: no
- Hook name: —
- Hook type: —
- Hook status: —

## Retrieval Triggers
- [trigger]

## Verification
- [ ] Hook fires in original scenario
- [ ] Hook produces intended behavior change
- [ ] No critical workflows broken
- Monitoring period: 2 weeks
- Monitoring started: —
- Last verified: —
EOF
  echo "Created template: $FILEPATH"
else
  # Stdin provided — write it
  cat > "$FILEPATH"
  echo "Created lesson: $FILEPATH"
fi

# Mirror to Trello Lessons board (Inbox list)
TRELLO_KEY=$(python3 -c "import keyring; print(keyring.get_password('openclaw','TRELLO_API_KEY'))" 2>/dev/null || echo "")
TRELLO_TOKEN=$(python3 -c "import keyring; print(keyring.get_password('openclaw','TRELLO_TOKEN'))" 2>/dev/null || echo "")

if [[ -n "$TRELLO_KEY" && -n "$TRELLO_TOKEN" && "$TRELLO_KEY" != "None" ]]; then
  INBOX_LIST="69e3e694635b28132b1ab3e9"
  DESC=$(head -30 "$FILEPATH" | sed 's/"/\\"/g')
  
  RESPONSE=$(curl -s -X POST "https://api.trello.com/1/cards" \
    -d "key=${TRELLO_KEY}" \
    -d "token=${TRELLO_TOKEN}" \
    -d "idList=${INBOX_LIST}" \
    --data-urlencode "name=Lesson ${PADDED}: ${TITLE}" \
    --data-urlencode "desc=${DESC}" \
    2>/dev/null)
  
  CARD_ID=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
  
  if [[ -n "$CARD_ID" ]]; then
    echo "Trello card created: ${CARD_ID}"
  else
    echo "WARNING: Trello mirror failed"
  fi
else
  echo "WARNING: Trello creds not available, skipping mirror"
fi

echo "Done: $FILEPATH"
