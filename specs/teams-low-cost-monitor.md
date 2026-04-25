# Teams Low-Cost Monitor — Implementation Spec

## Goal
Replace the killed Teams polling system with a webhook + preprocessor architecture that costs <$1/hr instead of >$80/hr.

## Why the Old System Was Expensive
The old Teams poller (`poll_all.py`) ran every 3 minutes via cron, waking Opus (Claude 4.6 Opus) for every poll cycle. Each wake sent the full 200K context window. When multiple chats had activity, sessions compacted and re-sent context repeatedly. One session hit 42 compactions = 42× the full context window re-sent at Opus pricing ($5/M input tokens).

## New Architecture

```
Microsoft Graph Webhooks (push)
    │
    ▼
Webhook Server (port 8443, already built)
    │
    ▼
Comms Preprocessor (Haiku 4.5 — ~$0.80/M input)
    │
    ├── IGNORE → log only (bot msgs, disabled chats)
    ├── LOG_ONLY → update state, no Opus wake
    └── PROCESS → wake Opus with minimal context
         │
         ▼
    Opus session (only for messages needing response)
```

### Cost Model
- **Haiku classifier:** ~500 tokens/call × $0.80/M = $0.0004/call
- **Even 100 messages/hr:** $0.04/hr for classification
- **Opus wakes:** Only for action_required/escalation messages (est. 5-10/hr during active hours)
- **Estimated total:** <$1/hr during active hours, ~$0/hr overnight
- **vs old system:** $80-160/hr (Opus polling every 3 min with full context)

## What Already Exists
1. `openclaw-dm/scripts/classify.py` — fast-path + Haiku fallback classifier (built by Claude Code, smoke-tested)
2. `openclaw-dm/scripts/teams_preprocessor.py` — orchestrator with state tracking (built, not wired)
3. `openclaw-dm/specs/comms-preprocessor.md` — full spec with policy.yaml / state.yaml schemas
4. `scripts/webhook-server/server.py` — webhook receiver (built, was running)
5. `scripts/webhook-server/lifecycle.py` — auto-discovers chats, creates webhook subscriptions
6. Per-chat policy.yaml files for all 15+ Teams chats in openclaw-dm/

## What Needs Building

### Phase 1: Wire Preprocessor to Webhook Server
- Modify `server.py` to call `teams_preprocessor.py` on incoming webhook
- Preprocessor fetches message via Graph API, classifies, routes
- PROCESS decisions → create OpenClaw session event (not full Opus wake)
- Ensure Haiku is called via RDsec endpoint (not direct Anthropic)

### Phase 2: Response Gate
- `teams-response-gate.js` hook module (built, needs integration)
- Blocks Opus from responding to read-only chats
- Enforces policy.yaml access levels

### Phase 3: Subscription Lifecycle
- Re-enable `lifecycle.py` cron (was working before shutdown)
- Auto-renew Graph API webhook subscriptions
- Auto-discover new chats

### Phase 4: Cost Monitoring
- Run token-usage-report skill hourly for first 24h
- Compare actual vs estimated cost
- Alert if hourly cost exceeds $5

## Safety Rails
- `enabled: false` by default — requires explicit turn-on
- Unknown chats default to read-only + require approval
- Response gate blocks sends to disabled/read-only chats
- Audit log for every classification decision
- Kill switch: disable webhook subscriptions via lifecycle.py

## Success Criteria
- Teams messages are received and classified within 30s
- Haiku handles 95%+ of incoming messages (no Opus for noise/fyi)
- Hourly token cost < $1 during active hours
- Zero unintended messages sent to read-only chats
- Joel can see audit log of all decisions
