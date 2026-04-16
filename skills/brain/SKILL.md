---
name: brain
description: >
  Query the unified brain for analysis of all monitored channels (GitHub, Teams, Signal).
  Use when the user asks about repos, issues, PRs, team activity, project status,
  customer data, tasks, or anything requiring cross-channel awareness.
  The brain has context from all communication channels and three-tier memory.
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins:
        - curl
---

# Unified Brain Query

You have access to a unified brain service that monitors GitHub repos, Teams chats,
and webhooks. It has full context across all channels and three-tier memory
(hot events, project summaries, global patterns).

## How to Query

Send the user's question to the brain's /ask endpoint. The brain analyzes with full
cross-channel context and conversation history, then returns a response.

### Query Command

The brain runs on the Windows host. Determine the host IP first, then query:

```bash
BRAIN_HOST=$(ip route show default | awk '{print $3}')
curl -s -X POST "http://${BRAIN_HOST}:8790/ask" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q "$QUESTION" '{question: $q, source: "signal", author: "joel", channel: "signal-dm", format: "signal"}')"
```

Replace `$QUESTION` with the user's actual message.

### Response Format

The response is JSON with a `text` field containing the brain's plain-text answer:
```json
{"text": "The brain's response here"}
```

Return the `text` value directly to the user. Do not wrap it in additional formatting.

### Error Handling

If curl fails or returns an error, tell the user:
"Brain service is not reachable. Make sure unified-brain is running on the host machine."

### Additional Endpoints

You also have direct access to the brain's data API:

**Search events** (full-text search):
```bash
curl -s "http://${BRAIN_HOST}:8790/search?q=SEARCH_TERM&limit=10"
```

**List recent events** (with optional filters):
```bash
curl -s "http://${BRAIN_HOST}:8790/events?source=github&hours=48&limit=20"
curl -s "http://${BRAIN_HOST}:8790/events?author=alice&channel=repo-name"
```

**Store new information**:
```bash
curl -s -X POST "http://${BRAIN_HOST}:8790/events" \
  -H "Content-Type: application/json" \
  -d '{"source":"signal","channel":"signal-dm","event_type":"note","author":"joel","body":"Customer X renewed license"}'
```

**Read memory summaries**:
```bash
curl -s "http://${BRAIN_HOST}:8790/memory"
curl -s "http://${BRAIN_HOST}:8790/memory?project=PROJECT_NAME"
```

Use /ask for conversational questions. Use the data endpoints when you need raw events,
search results, or want to store new information.

### What the Brain Knows

- **GitHub**: Issues, PRs, comments, reviews across all monitored repos
- **Teams**: Chat messages from configured Teams channels
- **Webhooks**: Any events pushed via the webhook adapter
- **Memory**: Three-tier memory with project summaries and global patterns
- **Conversation**: Remembers previous /ask exchanges per author for follow-ups

### Example Questions

- "What issues were opened today?"
- "Any activity in the Teams chat?"
- "What's the status of project X?"
- "Summarize what happened this week"
- "Follow up on that last question" (uses conversation history)
