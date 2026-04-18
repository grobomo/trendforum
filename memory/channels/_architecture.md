# Channel Memory Architecture

> **Doctrine:** Every communication channel uses the same granular, modular memory structure. Improvements to one channel's system automatically apply to all others. Unix philosophy — each file does one thing, standardized format, plug-and-play.

## Structure

```
memory/channels/
├── _architecture.md          # THIS FILE — the standard (never channel-specific)
├── {channel}/
│   ├── _overview.md          # Channel-wide: roster, policies, routing, access
│   ├── {entity}.md           # Per-entity context (chat, repo, board, contact, etc.)
│   └── ...
```

### Channel → Entity Mapping

| Channel  | Entity granularity     | Naming convention            |
|----------|------------------------|------------------------------|
| teams    | per-chat               | `coconut-private.md`, `coconut-molty.md` |
| slack    | per-channel/DM         | `all-misfits.md`, `joel-dm.md` |
| github   | per-repo               | `openclaw.md`, `hook-runner.md` |
| email    | per-contact/thread     | `dan-toresi.md`, `ep-v1-thread.md` |
| trello   | per-board              | `todo-list.md`, `comm-tracking.md` |

## Standard Entity File Template

Every entity file follows this structure:

```markdown
# {Entity Name}

## Identity
- Channel: {channel}
- Entity ID: {platform ID if applicable}
- Access: {read-write | read-only | disabled}
- Participants: {who's in this chat/repo/thread}

## Active Context
{What's currently being discussed or worked on — refreshed each session}

## Pending Actions
{Open items requiring follow-up, with timestamps}

## Key Decisions
{Decisions made in this context — date-stamped, with WHY}

## Session Log
### {YYYY-MM-DD HH:MM}
{Brief session summary — what happened, what changed}
```

## Rules

1. **One file per entity.** Never mix chat contexts in the same file.
2. **_overview.md is the index.** Lists all entities, access policies, and routing rules. Lightweight.
3. **Session logs roll up.** Keep last 3-5 sessions in entity files. Older context → daily notes or MEMORY.md.
4. **Same template everywhere.** If you add a section to one entity file, consider adding it to all.
5. **Load only what you need.** When composing a reply for a specific chat, load ONLY that chat's entity file + the channel _overview.md. This prevents context bleed.
6. **Improvements propagate.** Any structural improvement to one channel's memory must be applied to all channels. Update this architecture doc when the standard evolves.

## Why This Matters

- **Prevents cross-chat context bleed** — the root cause of the 21:52 misfire
- **Scales to any channel** — add a new platform by creating a new directory + _overview.md
- **Enables Gate 1 pre-compose checks** — scoped context loading = scoped replies
- **Modular maintenance** — archive one entity without touching others
- **Unix philosophy** — small, composable, standardized units since 1970

---

_Established: 2026-04-18 | Author: Joel Ginsberg + Coconut_
