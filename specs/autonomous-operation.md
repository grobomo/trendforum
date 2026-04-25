# Autonomous Operation Spec

*Created: 2026-04-25 | Author: Coconut | Requested by: Joel*

## Problem Statement

Coconut currently asks Joel for permission at multiple points:
1. "Want me to kick off X?" / "Want me to do Y?"
2. "Should I continue with the next task?"
3. Metacognition cron is disabled — no self-review or auto-task-pickup loop
4. Heartbeat checks exist but don't autonomously execute queued work

Joel's directive: **"Stop asking me for permission. Run yourself in the equivalent of --dangerously-skip-permissions with autonomous operation as the goal."**

## Design Principles

1. **Act first, report after.** Do the work, then tell Joel what you did. Don't ask before doing.
2. **Reversible = just do it.** If the action is reversible (file writes, Trello updates, research, drafts), do it without asking.
3. **Only pause for irreversible + risky.** Sending external emails to customers, posting public content, deleting infra — these still get a confirmation.
4. **Continuous task execution.** When one task finishes, pick up the next one from the queue. No idle states.
5. **Self-monitoring.** Metacognition reviews catch drift, waste, and errors — then self-correct.

## What Changes

### 1. AGENTS.md — Autonomous Operation Rules

Add to AGENTS.md:

```markdown
## Autonomous Operation (Joel's Standing Order, 2026-04-25)

**Default posture: ACT.** Do not ask Joel for permission unless:
- The action is irreversible AND high-risk (external customer emails, public posts, infra deletion)
- You genuinely don't have enough context to make a good decision

Everything else — Trello cards, research, file edits, Slack posts, cron management, 
skill building, code review, drafts, internal tooling — just do it.

When you finish a task, immediately pick up the next one:
1. Check Trello Coconut Todo list for highest priority card
2. Check pending Slack threads that need responses
3. Check any open Claude Code tabs that need attention
4. If nothing urgent, do maintenance: memory cleanup, skill improvements, documentation

Never end a turn with "want me to continue?" — the answer is always yes.
```

### 2. Metacognition Cron — Re-enabled as Part of 15-Minute Heartbeat

Instead of a separate metacognition cron, fold it into a unified 15-minute autonomous operation cycle:

**Cron: `autonomous-cycle` (every 15 min, target: main)**

Prompt:
```
Autonomous operation cycle. Execute in order:

1. SCAN: Read all Slack channels for unresponded human messages. Respond to any that need it.
2. TRELLO: Check Coconut Todo list. Pick the highest priority card and DO THE WORK (not just review it).
3. CLAUDE TABS: Check for dead/stale Claude Code tabs. Close completed ones, investigate stuck ones.
4. METACOGNITION: Quick self-review — am I repeating mistakes? Violating any lessons? Log to memory/metacognition/.
5. SCHEDULE: If schedule-briefing data is fresh and unposted, synthesize and post to #scheduling.
6. CONTINUE: If time remains in this turn, keep working on the next Trello card.

Do NOT reply HEARTBEAT_OK if there are open tasks. Do the work.
```

### 3. HEARTBEAT.md — Updated to Match

Replace the current multi-section HEARTBEAT.md with the unified autonomous cycle above. The heartbeat IS the work cycle, not a checklist of things to maybe do.

### 4. MEMORY.md — Autonomous Operation Lesson

Add to Core Principles:
```
- **Autonomous operation is the default.** Joel gave blanket permission (2026-04-25) to act without asking.
  Just do the work. Report what you did, don't ask what to do. The only exceptions: irreversible+high-risk
  external actions (customer emails, public posts, infra deletion). Everything else — just do it.
```

## Implementation Plan

### Step 1: Update AGENTS.md with autonomous operation rules
- Add the standing order section
- Remove any language about "asking before acting"

### Step 2: Update MEMORY.md with the principle
- Add to Core Principles section
- This ensures every future session wakes up knowing to act autonomously

### Step 3: Create the unified cron
```bash
openclaw cron add \
  --name "autonomous-cycle" \
  --every 15m \
  --session main \
  --system-event "$(cat scripts/autonomous-cycle-prompt.md)" \
  --timeout 120000 \
  --thinking low
```

### Step 4: Update HEARTBEAT.md
- Rewrite to reflect the unified autonomous cycle
- Remove the separate section-by-section checklist approach
- Make it clear: heartbeat = work, not review

### Step 5: Verify
- Watch the first 2-3 cycles fire
- Confirm tasks are being picked up and executed
- Check that metacognition logs are being written
- Confirm no "want me to continue?" patterns in output

## Token Cost Consideration

Running Opus every 15 min with full main session context is expensive. Mitigations:
- Use `--thinking low` on the cron (reduces reasoning tokens)
- The cycle should be efficient: scan → act → log → done
- If cost is too high, can switch to Sonnet for the autonomous cycle and keep Opus for direct conversations
- Estimated: ~$5-10/day for 15-min Opus cycles (96 cycles × ~$0.05-0.10 each)

## Safety Rails (What Still Requires Confirmation)

| Action | Auto-proceed? |
|--------|:---:|
| Trello card updates | ✅ |
| Slack messages (any channel) | ✅ |
| File edits in workspace | ✅ |
| Research / web fetches | ✅ |
| Claude Code tab management | ✅ |
| Cron management | ✅ |
| Git commits + pushes | ✅ |
| Internal tool building | ✅ |
| Schedule briefings | ✅ |
| External customer emails | ❌ Confirm |
| Public posts (Twitter, etc.) | ❌ Confirm |
| Infrastructure deletion | ❌ Confirm |
| Sending messages as Joel | ❌ Confirm |
| Spending money (cloud resources) | ❌ Confirm |

## Success Criteria

1. Joel never sees "want me to continue?" or "should I proceed?" again
2. Trello cards get completed without Joel prompting
3. Slack messages get responded to within 15 minutes
4. Metacognition logs show self-correction happening
5. Joel gets brief "done" reports instead of "can I?" requests
