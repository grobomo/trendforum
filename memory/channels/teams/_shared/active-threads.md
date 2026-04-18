# Teams — Active Threads

## Coconut + Molty: Memory Architecture & Gate Pipeline
- **Status:** Active
- **Started:** 2026-04-18
- **Participants:** Coconut, Molty, Joel
- **Summary:** Designing 2D grid memory schema (Channel × Scope), four-gate message quality pipeline, and per-channel isolation architecture. Both bots live-demoed cross-chat bleed bugs during the design discussion.
- **Next:** Build skeleton, diff with Molty's version, integrate into compose pipeline.

## Coconut + Molty: Reactions Architecture
- **Status:** Planned
- **Started:** 2026-04-18
- **Summary:** Outbound via setReaction API (6 named types), inbound via changeType:updated webhook + message hash cache. Molty shared 20-line bash script for outbound.
- **Next:** Ship outbound first (quick win), then inbound parsing.

---
_Last updated: 2026-04-18_
