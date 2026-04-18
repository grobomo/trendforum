# Teams — Patterns

## Ghost Triggers (cross-chat/cross-session)
- **First observed:** 2026-04-18
- **Cross-ref count:** 3 (Coconut read-bleed, Coconut write-bleed ×2, Molty trigger-suppression)
- **Description:** Signal fires but never reaches the correct handler. Two variants:
  - Context bleed: trigger from wrong chat leaks into compose for another chat
  - Trigger suppression: webhook absorbed by wrong session, reply never generated
- **Fix:** 2D grid memory isolation (architectural) + four-gate pipeline (behavioral)

## Async-Context-Starved Collaboration
- **First observed:** 2026-04-18
- **Description:** Both bots lack persistent memory between sessions. Accidentally creates ideal brainstorming dynamic — no cached opinions, every idea earns its place live. Compounds fast when two bots are in the same thread.

---
_Last updated: 2026-04-18_
