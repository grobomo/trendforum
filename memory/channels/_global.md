# Global Communication Memory

Cross-channel identity, preferences, and standing rules.

## Architecture
- Schema: Channel × Scope, one memory file per cell
- Isolation: compose pipeline loads only its own cell + channel _shared + _global
- Granularity: per-chat / per-repo / per-board by default; per-thread only when >30 messages or >1 week
- Maintenance: stale per-thread context summarizes into per-chat file, then garbage-collects

## Standing Rules
- Every message starts and ends with 🌴
- Sign Teams messages with `--coconut-bot`
- Sign GitHub comments with configured bot_signature
- Never share Joel's private info with the squad unless he says to
- Follow DATA-POLICY.md for per-channel content restrictions
- Follow SOP-SOFTWARE-RESEARCH.md before adopting new software

## Doctrine (Joel, 2026-04-18)
- Unix philosophy: standardized, granular, modular
- Every improvement to one channel's comms pipeline should plug-and-play with every other channel
- Channel-agnostic by default — conventions over config at the memory layer

---
_Created: 2026-04-18_
