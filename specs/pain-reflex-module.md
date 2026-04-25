# Pain Reflex Module — Spec

> "Haiku is the limbic system. It doesn't write lessons — it flags pain so Opus can reflect."
> — Joel, 2026-04-24

## Concept

Humans learn from pain — not from instructions. The amygdala fires a fast, dumb signal ("that hurt") and the prefrontal cortex does the actual learning later. This module replicates that:

- **Haiku** = amygdala. Watches conversations. Detects correction, frustration, repetition.
- **Opus** = prefrontal cortex. Reads the todo, reviews the conversation, writes the lesson.

## Architecture

```
Joel says something ──→ message_sent hook (fire-and-forget)
                              │
                              ▼
                     Haiku analyzes last N messages
                     "Is Joel correcting/frustrated/repeating?"
                              │
                     ┌────────┴────────┐
                     │ NO              │ YES
                     │ (do nothing)    │
                     │                 ▼
                     │        Append todo item to
                     │        openclaw-dm/<channel>/todo.md
                     │                 │
                     │                 ▼
                     │        git commit + push
                     │        (→ GitHub Actions → Trello)
                     │                 │
                     │                 ▼
                     │        Opus picks up todo later,
                     │        reviews conversation,
                     │        writes lesson to memory/lessons.md
                     └─────────────────┘
```

## Hook Type

`message_sent` (after_tool_call on message sends) — fire-and-forget, non-blocking.

This runs AFTER messages are delivered, never blocks conversation flow.

## Pain Signal Detection (Haiku's ONLY job)

Haiku gets a simple prompt with the last 3-5 messages and answers ONE question:

```
Is the human expressing any of these signals?
1. CORRECTION — "No, I meant...", "That's not what I asked", rephrasing a request
2. FRUSTRATION — explicit annoyance, repeating themselves, "I already said..."
3. REPETITION — asking the same thing they asked before (agent missed it)
4. MISTAKE_CALLED — "You shouldn't have done X", "Why did you do Y?"
5. NONE — normal conversation, no pain signal

Respond with EXACTLY one word: CORRECTION, FRUSTRATION, REPETITION, MISTAKE_CALLED, or NONE
If unsure, say NONE.
```

That's it. No lesson analysis. No summary. One word.

## Todo Item Format

When Haiku detects a signal, append to the relevant `openclaw-dm/<channel>/todo.md`:

```markdown
- [ ] 🔥 Lesson needed: <SIGNAL_TYPE> detected (ref: <timestamp>)
  - Context: <1-line summary of what triggered it, from Haiku>
  - Conversation: review last 5 messages in <channel> around <timestamp>
  - Write lesson to memory/lessons.md when processed
```

## Channel Mapping

Map the current conversation context to the right todo.md:

| Context | todo.md path |
|---|---|
| Slack Joel DM | `dm/todo.md` |
| Slack #all-misfits | `slack/all-misfits/todo.md` |
| Slack #coco-chat | `slack/coco-chat/todo.md` |
| Teams chat | `teams/<chat-label>/todo.md` |
| Default/unknown | `dm/todo.md` |

## Implementation

### Where it lives

Add as a new hook in `coconut-guardrails/index.ts` — it already has the Haiku calling infrastructure (`callInnerVoice` pattern). This is a new `message_sent` listener, not a new plugin.

### What it needs

1. Access to recent message history (last 3-5 messages in current conversation)
   - Use `event` context from the `message_sent` hook
   - May need to read from channel state or session context
2. Haiku API call (same auth pattern as inner voice)
3. File write to openclaw-dm todo.md (local clone)
4. Git commit + push (exec or child_process)

### Rate limiting

- Max 1 pain check per conversation per 5 minutes (debounce)
- Cache last check timestamp per channel in memory
- If Haiku call fails → log and skip (never block, never retry aggressively)

### Audit logging

Every detection logged to guardrails audit log:
```json
{
  "hook": "message_sent",
  "module": "pain-reflex",
  "channel": "slack:D0ATWPM4DTK",
  "signal": "CORRECTION",
  "todoPath": "dm/todo.md",
  "timestamp": "2026-04-24T18:00:00Z"
}
```

## What Opus Does (Not Part of This Module)

When Opus picks up the `🔥 Lesson needed` todo item:

1. Read the referenced conversation (message history around the timestamp)
2. Understand WHY Joel corrected / was frustrated
3. Identify the root cause (wrong assumption? missed instruction? repeated mistake?)
4. Write a proper lesson to `memory/lessons.md` with the standard format:
   `- [YYYY-MM-DD] [#tag] Lesson title — why + structural fix`
5. Check off the todo item `[x]`
6. If the lesson suggests a structural fix (new hook module, config change, etc.), create a separate todo for that

## Non-Goals

- Haiku does NOT write lessons (too shallow)
- Haiku does NOT analyze what went wrong (that's Opus's job)
- This module does NOT block any actions (fire-and-forget only)
- This module does NOT send notifications to channels (todo → Trello sync handles visibility)

## Implementation Order

1. [ ] Clone openclaw-dm repo locally (if not already)
2. [ ] Add `message_sent` hook to coconut-guardrails with pain signal detection
3. [ ] Implement channel → todo.md path mapping
4. [ ] Implement todo item append + git commit/push
5. [ ] Add debounce (1 check per channel per 5 min)
6. [ ] Test: simulate a correction, verify todo item appears
7. [ ] Test: verify Opus picks up the todo and writes a lesson

---

*Spec author: Coconut | Date: 2026-04-24 | Requested by: Joel*
