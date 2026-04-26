# Conflict Resolution Module — Reference

## When This Fires

A conflict exists when:

- A Trello card spec says "do X" but a lesson says "X is impossible/wrong"
- Two lessons give contradictory guidance
- A hook module needs a capability the hook system doesn't support
- Existing knowledge says the planned approach won't work

## Resolution Process

### 1. Detect

Write a conflict detection summary:

```
CONFLICT DETECTED:
- Source A: [lesson/card/spec] says [X]
- Source B: [lesson/card/spec] says [Y]
- Why they conflict: [explanation]
```

### 2. Research

Before deciding, research ALL sides:

- Read full text of every lesson involved (`memory/lessons/*.md`)
- Read the spec/card that triggered the conflict
- Check if any hooks or gates reference the conflicting knowledge
- `memory_search` for prior discussions about the topic
- Check OpenClaw docs if architecture questions are involved
- Check openclaw-gates plugin for existing enforcement patterns

### 3. Document

Create a CR document at `memory/conflict-resolutions/CR-{NNN}-{slug}.md`.

Template:

```markdown
# CR-{NNN}: {Short Title}

## Status
`draft` | `pending-review` | `resolved` | `applied`

## Date
{YYYY-MM-DD}

## Conflict Summary
One-line description.

## Side A
- **Source:** {lesson/card/spec/doc} — `{path or link}`
- **Says:** {quote or paraphrase}
- **Date written:** {when}

## Side B
- **Source:** {lesson/card/spec/doc} — `{path or link}`
- **Says:** {quote or paraphrase}
- **Date written:** {when}

## Research
### What the docs say
### What the code says
### Historical context
### Related lessons

## Options
### Option 1: {Name}
- Approach / Pros / Cons / Impact

### Option 2: {Name}
- Approach / Pros / Cons / Impact

## Decision
{Chosen option + reasoning — filled after resolution}

## Resolution Actions
- [ ] Update/retire affected lesson(s)
- [ ] Update spec/card if needed
- [ ] Create/update enforcement hook if needed
- [ ] Post to #coco-metacognition
- [ ] Update INDEX.md

## Resolved By
{human | self} — {name} — {date}
```

### 4. Decide

*Self-resolvable* (act immediately):
- Factual errors in lessons (docs/code prove otherwise)
- Outdated lessons (system changed since lesson was written)
- Lessons superseded by newer lessons

*Requires human input* (escalate):
- Architecture decisions with genuine trade-offs
- Conflicting operator instructions
- Irreversible consequences if wrong

### 5. Apply

After resolution:
- Update or retire the incorrect/outdated lesson
- Update specs or cards that referenced wrong info
- Create or update hooks/gates if needed
- Log resolution with status `applied`
- Post to `#coco-metacognition`
