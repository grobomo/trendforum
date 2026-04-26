---
name: conflict-resolution
description: >-
  Metacognition module for detecting and resolving conflicts between lessons,
  specs, hook architectures, and system knowledge. Use when: (1) a lesson
  contradicts a spec or card requirement, (2) two lessons conflict with each
  other, (3) a hook/gate approach is blocked by architectural constraints,
  (4) a decision requires choosing between competing approaches, (5) any
  situation where proceeding would violate existing documented knowledge.
  Triggers on: "conflict", "contradiction", "architecture conflict",
  "lesson conflict", "which approach", "design decision needed",
  "spec vs lesson", "can't do both".
  Required dependency: openclaw-gates (enforcement via Plugin SDK hooks).
---

# Conflict Resolution

Detect knowledge conflicts, research context, produce auditable decision documents, and
optionally enforce resolution-before-action via an openclaw-gates hook.

## When This Fires

You've hit a conflict when:

- A Trello card spec says "do X" but a lesson says "X is impossible/wrong"
- Two lessons give contradictory guidance for the same situation
- A hook module needs a capability the hook system doesn't support
- You're about to build something but existing knowledge says the approach won't work

## Resolution Process

### 1. Detect — Identify the conflict

Write a conflict detection summary:

```
CONFLICT DETECTED:
- Source A: [lesson/card/spec] says [X]
- Source B: [lesson/card/spec] says [Y]
- Why they conflict: [explanation]
```

### 2. Research — Gather full context

Before making any decision, research ALL sides:

- Read the full text of every lesson involved (`memory/lessons/*.md`)
- Read the spec/card that triggered the conflict
- Check if any hooks or gates reference the conflicting knowledge
- Search memory for prior discussions about the topic: `memory_search`
- Check OpenClaw docs if architecture questions are involved
- Check the openclaw-gates plugin for existing enforcement patterns

Document what you find in step 3.

### 3. Document — Write the decision document

Create a conflict resolution document at:

```
memory/conflict-resolutions/CR-{NNN}-{short-slug}.md
```

Use the template at `{baseDir}/references/cr-template.md`.

The document must include:
- Both sides of the conflict with full quotes
- Research findings (what docs/code/history say)
- Options considered with pros/cons
- Recommended resolution
- Impact analysis (what changes if we pick this option)
- Status: `draft` → `pending-review` → `resolved` → `applied`

### 4. Decide — Apply or escalate

*Self-resolvable* (act immediately):
- Factual errors in lessons (lesson says X, but docs/code prove Y)
- Outdated lessons (system changed since lesson was written)
- Lessons that were already superseded by newer lessons

*Requires human input* (escalate to Joel):
- Architecture decisions with trade-offs (no objectively correct answer)
- Conflicting operator instructions
- Anything where the "wrong" choice has irreversible consequences

When escalating, post the CR document summary to Joel's DM with a clear question.

### 5. Apply — Update affected artifacts

After resolution:
- Update or retire the incorrect/outdated lesson
- Update any specs or cards that referenced wrong information
- Create or update hooks/gates if the resolution changes enforcement
- Log the resolution in `memory/conflict-resolutions/` with status `applied`
- Post to `#coco-metacognition` for visibility

## Enforcement via openclaw-gates

This skill requires the `openclaw-gates` Plugin SDK plugin for enforcement.

### How enforcement works

The openclaw-gates plugin can enforce conflict resolution via the `before_tool_call` hook.
When the conflict-resolution gate detects that a spec/build action conflicts with existing
lessons, it blocks the action and requires a CR document before proceeding.

To add the enforcement gate, follow the openclaw-gates plugin architecture:

1. Add a `conflictResolution` config section to the openclaw-gates plugin config
2. The gate checks if a `write` or `edit` to spec/build files has a corresponding
   CR document when lessons flag a conflict
3. Block with a redirect to this skill's resolution process

See `{baseDir}/references/gate-integration.md` for the gate implementation pattern.

### Why openclaw-gates (not hook-runner)

Per lesson 002 (`memory/lessons/002-managed-vs-plugin-hooks.md`):
- Managed hooks (`~/.openclaw/hooks/`) can only observe events — they cannot block tool calls
- Plugin SDK hooks (openclaw-gates) support `before_tool_call` with blocking capability
- Enforcement MUST use Plugin SDK hooks; managed hooks are insufficient

This is itself an example of the conflict this skill resolves: "build a blocking hook"
(requirement) vs "managed hooks can't block" (architectural constraint). The resolution:
use Plugin SDK hooks via openclaw-gates.

## Relationship to Other Skills

| Skill | Relationship |
|---|---|
| `hook-runner-module-manager` | Manages claude-code-gates modules (different plugin, different target) |
| `openclaw-gates` (plugin) | *Required dependency* — enforcement layer for conflict resolution |
| `skill-creator` | Used to build this skill; CR docs may trigger new skill creation |

## File Layout

```
memory/conflict-resolutions/
├── CR-001-hook-architecture-blocking.md
├── CR-002-...
└── INDEX.md  (auto-maintained summary of all CRs)
```
