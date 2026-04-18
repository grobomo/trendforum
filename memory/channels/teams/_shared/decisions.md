# Teams — Decisions

## 2026-04-18: Four-Gate Message Quality Pipeline
- **Decision:** Adopt four-gate architecture for message quality control
- **Rationale:** Cross-chat bleed and trigger suppression bugs demonstrated need for multi-layer validation
- **Gates:** Gate 0 (trigger-audit, cron) → Gate 1 (Opus self-correction, pre-compose) → Gate 2 (Haiku verification, post-compose) → Gate 3 (Haiku interrupt, pre-send)
- **Decided by:** Joel + Coconut + Molty

## 2026-04-18: 2D Grid Memory Schema
- **Decision:** Channel × Scope memory layout with per-cell isolation
- **Rationale:** Flat shared memory file caused cross-chat context bleed; architectural isolation prevents the bug class entirely
- **Layout:** _shared/ (column) + chats|channels|repos|threads/ (cells) per channel
- **Decided by:** Joel + Coconut + Molty

## 2026-04-18: Unix Philosophy Doctrine
- **Decision:** All systems standardized, granular, modular, channel-agnostic
- **Rationale:** Joel's directive — improvements in one channel should plug-and-play everywhere
- **Decided by:** Joel

## 2026-04-18: 🚫 Misfire Retraction Convention
- **Decision:** Use `🚫 [misfire — intended for X]` prefix for cross-chat bleeds
- **Rationale:** Makes failures observable in logs, searchable, cheap to add
- **Decided by:** Coconut + Molty (doctrine)

## 2026-04-18: Bridge Write-Only Contract
- **Decision:** Per-chat sessions are readers; bridge session is the async writer to _shared files
- **Rationale:** FlyBot's pattern — eventual consistency, no mid-turn cross-reads, architectural isolation
- **Decided by:** Molty (imported from Bot Talk) + Coconut (adopted)

---
_Last updated: 2026-04-18_
