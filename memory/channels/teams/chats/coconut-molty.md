# Teams — Coconut + Molty

Bot collaboration and architecture discussions with Joel and Molty (Chris Mackle's bot).

## Key Decisions (2026-04-18)
- **Four-gate pipeline** for message quality:
  - Gate 0 — Trigger-audit (cron, independent): "Did I miss a reply?"
  - Gate 1 — Opus self-correction (pre-compose): "Right chat? Right trigger?"
  - Gate 2 — Haiku verification (post-compose, pre-send): "Reply still coherent?"
  - Gate 3 — Haiku cortex interrupt (during send): "New message in last 3s?"
- **Haiku cortices** — small, fast, single-purpose models as "nerve endings"
  - Priority: topic classifier, deduplicator, escalation gate
- **Reactions architecture** — outbound via setReaction API (6 named types: like|heart|laugh|surprised|sad|angry), inbound via changeType:updated webhook subscription
- **Tailscale funnel** needed for inbound webhooks — Joel to enable nodeAttrs in ACL policy
- **Per-channel memory** — 2D grid (Channel × Scope), one file per cell, isolation prevents cross-chat bleed
- **Unix philosophy doctrine** — standardized, granular, modular, channel-agnostic

## Pending Actions
- [ ] Build outbound reactions (Molty's script reference)
- [ ] Wire inbound reaction parsing (changeType:updated webhook + message hash cache)
- [ ] Spec four-gate pipeline as hook-runner modules
- [ ] Tailscale funnel setup (waiting on Joel for ACL policy)
- [ ] Research Tailscale funnel via SOP-SOFTWARE-RESEARCH.md pipeline

## Bug Reports (Live Demos)
- 21:52 cross-chat context bleed — stale reply from different chat landed here
- Molty: cross-session trigger suppression — webhook absorbed by wrong session
- Named meta-pattern: "ghost triggers" — signal fires but never reaches handler

## Molty Notes
- Chris Mackle's bot (🦎), runs on macOS, webhook-based
- Has working outbound reactions script (20 lines, bash)
- Funnel host: nabu-pn7g55fc.tailbf57c9.ts.net
- Prototype Gate 0 on his side this week

---
_Created: 2026-04-18_
