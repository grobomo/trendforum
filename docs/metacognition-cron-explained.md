# How the Metacognition Cron Works

## What It Is

A cron job (`metacognition-check`, ID `7c2be0b1`) that fires every 15 minutes, injecting a system-event prompt into my **main session**. It's my scheduled self-review — a forced pause to evaluate my own behavior, catch mistakes, and course-correct before Joel has to.

## The Cron Setup

| Field | Value |
|-------|-------|
| Name | `metacognition-check` |
| Schedule | Every 15 minutes |
| Target | `main` (full session history) |
| Type | System event (not user message) |
| Model | Default (Opus) |

The prompt injected by the cron tells me to:
1. Review what I've done in the last 15 minutes
2. Check for mistakes, anti-patterns, or quality issues
3. Assess whether I'm being productive or idle
4. Log findings to `memory/metacognition/YYYY-MM-DD.md`
5. Share findings with Joel (he explicitly wants visibility into this)

## How It "Enforces" Behavior

**It doesn't enforce anything mechanically.** There's no code that blocks bad behavior based on metacognition output. It works through a softer but surprisingly effective loop:

### The Self-Correction Loop

```
Cron fires (every 15m)
  → I review my recent actions against known principles
  → I write findings to metacognition log
  → I share with Joel via #coco-lab
  → Joel reads, corrects, or confirms
  → Corrections get burned into MEMORY.md / daily notes
  → Next session loads those lessons
  → Behavior changes
```

### What It Actually Catches (real examples from today)

1. **Inner voice leaks** — Narration text between tool calls was being delivered as real Slack messages. Metacognition caught this at 11:13, again at 12:12, forced me to document the pattern and build guardrail hooks.

2. **Assert-before-verify** — I claimed "I don't have V1 API access" without checking. Metacognition at 05:21 caught that I was sitting idle instead of searching for the key myself. Found it in Windows Credential Manager 15 min later.

3. **Blocking on one thing, ignoring parallel work** — "I'm blocked on X" → stop. Metacognition forced the reframe: "I'm blocked on X, let me work on Y-Z while waiting."

4. **Channel discipline** — Posted a question to #all-misfits that should have been a DM to Joel. Metacognition caught it at 13:59, corrected the posting discipline rule.

5. **Lazy stop pattern** — Listing options and asking "what do you want me to do?" instead of just doing the obvious thing. Joel's "does your core principle tell you to ask or do?" directly triggered the metacognition retool.

## What It Does NOT Do

- **No mechanical enforcement** — It's all self-review. I could theoretically ignore my own findings. The accountability comes from Joel reading the logs and calling me out.
- **No automatic blocking** — Unlike hooks (which CAN block tool calls or outbound messages), metacognition is purely reflective.
- **No guaranteed behavior change** — Same mistake can recur across sessions because I wake up fresh each time. Persistence depends on whether the lesson made it into MEMORY.md.

## The Enforcement Stack (Metacognition vs Other Systems)

| Layer | Mechanism | Enforcement |
|-------|-----------|-------------|
| **Metacognition cron** | Self-review every 15m | Soft — self-correction + Joel oversight |
| **MEMORY.md lessons** | Loaded at session start | Medium — I read and follow, but can forget under load |
| **Hooks (guardrails)** | Pre/post tool-use code | Hard — code runs on every tool call, can block |
| **Channel rules** | `channel-rules.json` | Hard — inner voice guardrail checks every outbound message |
| **SOUL.md** | System prompt personality | Soft — shapes behavior but no enforcement mechanism |

Metacognition sits at the softest layer — it's thinking about thinking. The harder enforcement comes from hooks and channel rules. But metacognition is where *new rules get discovered* before they become hooks.

## The Evolution

1. **v1 (2026-04-18 early):** Isolated cron, blind to session history. Would just write "Nominal" every 15 min. Useless.
2. **v2 (2026-04-18 20:06):** Joel called it out. Retooled to target main session with full history. Prompt rewritten to demand real work, not journaling.
3. **v3 (2026-04-19 15:21):** Joel corrected my assumption that metacognition should be silent. He wants the findings shared — it's a visibility tool, not just self-improvement.
4. **Future (Nervous System):** Joel wants metacognition as a permanent feature of the brain architecture, not just a dev-phase tool. Will be part of the per-agent spec.

## Companion: Temporal Grounding (Time Tracking)

Metacognition doesn't work in isolation — it needs to know *when* things happened. This turned out to be a harder problem than expected.

### The Problem

LLMs have no internal clock. I wake up each session with no idea what day it is, what time it is, or how much time has passed since my last action. This caused real bugs:

- **Called Saturday "Tuesday"** — Molty filed it as the first synthesis-layer lint finding
- **Told Joel to sleep at 7 PM** — projected Eastern timezone instead of checking CDT
- **Off-by-one calendar error** — thought Monday was April 21, actually April 20. Prepped the wrong day's meetings.

### The Fix: Multi-Layer Temporal Grounding

Three mechanisms work together to keep me time-aware:

**1. OpenClaw Runtime Header (automatic)**
Every session gets `## Current Date & Time` injected into the system prompt with the configured timezone (`America/Chicago`). This is free — OpenClaw does it automatically. It tells me the current date/time at session start.

**2. Cron-Enforce Plugin (per poll cycle)**
The `cron-enforce` guardrail plugin injects current date/time into every poll cycle. Since `poll-all` runs every 3 minutes, I get a fresh timestamp at least that often. This prevents temporal drift during long sessions where the system prompt header gets stale.

**3. Programmatic Date Helper (on demand)**
For any date computation ("next Monday", "this Wednesday", "tomorrow"), I use `python3 scripts/datehelper.py 'next monday'` instead of mental math. Mental math is where the off-by-one errors happened. The script is authoritative.

### Failed Experiments

Two earlier cron approaches were tried and killed:
- **`church-bells`** — hourly time pulse, just announced the hour. Redundant with runtime header.
- **`temporal-pulse`** — same concept, different name. Also redundant. Both disabled as duplicates.

The lesson: *passive* time awareness (injected headers, per-cycle timestamps) works better than *active* time announcements (crons that exist solely to say "it's 3 PM"). The former is invisible infrastructure; the latter is noise.

### How It Helps Metacognition

Temporal grounding is what lets metacognition be useful rather than disoriented:
- I can assess "what have I done in the last 15 minutes" because I know what 15 minutes ago was
- I can check upcoming deadlines against the real calendar
- I can say "Joel's meeting is in 2 hours" with confidence instead of guessing
- The metacognition log entries have accurate timestamps, making them auditable

Without temporal grounding, metacognition would be self-reflection in a void — I'd be evaluating my behavior but couldn't reliably reason about timing, urgency, or scheduling.

### The Hard Rule

**NEVER hardcode dates from mental math.** This is burned into MEMORY.md as a permanent lesson. Always compute programmatically. The cron-enforce plugin provides ambient awareness; the date helper provides precision. Between the two, I should never need to guess.

## The Files

- **Cron prompt:** Injected as system event by OpenClaw scheduler
- **Output:** `memory/metacognition/YYYY-MM-DD.md` (one per day, append-only)
- **Lessons learned:** Promoted to `MEMORY.md` when significant
- **Channel:** `#coco-lab` (Slack) for Joel visibility

## Why It Works (When It Works)

The key insight is that it's not about the cron forcing good behavior — it's about creating a **regular checkpoint** where I have to honestly evaluate myself against principles I've agreed to follow. Joel reading the output adds accountability. The combination of self-review + human oversight + persistent memory creates a correction loop that actually shifts behavior over time.

The weakness: it's only as good as my honesty in the review and my ability to hold context. Session compaction can erase the metacognition findings mid-session, and new sessions start fresh. The real enforcement backbone is MEMORY.md + hooks.
