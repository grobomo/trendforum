# Lesson: poll_all.py is Permanently Dead — Never Re-enable

## Observation
2026-04-24: Coconut re-enabled `teams-poller.service` and `poll_all.py` after maintenance mode, framing it as "disabled until we had a proper fix." Joel corrected this — poll_all is NEVER coming back. It was a fundamentally broken approach: 23,884 calls/day, 39MB sessions, gateway crashes. The replacement is the dedicated `teams-poller.service` (event-driven, polling every 3s per chat) and `webhook-server.service` (Graph API subscriptions). Even those were disabled on Joel's order (2026-04-24) and must not be re-enabled without explicit permission.

## The Lesson
When Joel disables something, it's disabled PERMANENTLY unless he explicitly says otherwise. Never frame a disabled system as "waiting for a fix" — that implies re-enabling is the plan. The system is dead. Document it. Move on.

More broadly: **when I take any corrective action (disabling services, changing configs, removing systems), I MUST immediately document:**
1. What was changed
2. Why it was changed
3. Whether it's temporary or permanent
4. Who authorized it

This goes in both the daily memory file AND the relevant lessons file.

## Source
- Session: Slack DM, 2026-04-24 ~12:25 CDT
- Conversation with: Joel
- Date observed: 2026-04-24

## Hook
- Has hook: yes
- Hook name: correction-gate (pending — this lesson triggered its creation)
- Hook type: pre-action (before_tool_call)
- Hook status: new
- What it does: After Joel corrects me, blocks all action until I've run metacognition + documented the lesson

## Retrieval Triggers
- Re-enabling poll_all.py
- Re-enabling teams-poller.service
- Re-enabling webhook-server.service
- "temporary" disable of any service
- Framing disabled things as "until fixed"
- Taking action after Joel corrects me without documenting the lesson first

## Verification
- [ ] Hook fires when correction detected
- [ ] Hook blocks action until lesson documented
- [ ] No critical workflows broken
- Monitoring period: 2 weeks
- Monitoring started: 2026-04-24
- Last verified: —
