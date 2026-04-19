# Lesson: Verify External State Before Claiming

## Observation
2026-04-18: Metacognition cron detected pattern where agent hallucinated infrastructure state (EP AWS account status, service statuses) by trusting session memory or cached context instead of independently verifying via API/CLI. "Trust-chaining" — claiming something is true because an earlier message said so, without re-checking.

## The Lesson
Before making any claim about external state (service status, API responses, infrastructure, account status), independently verify it with a real tool call. Never rely on session memory or prior conversation context for current state. If you can't verify, say "I haven't checked" instead of asserting.

## Source
- Session transcript: metacognition cron observation, 2026-04-18 ~22:09 CDT
- Conversation with: Joel (follow-up 2026-04-19)
- Date observed: 2026-04-18

## Hook
- Has hook: yes
- Hook name: verify-before-claiming
- Hook type: post-action (audit outbound messages for unverified state claims)
- Hook status: new

## Retrieval Triggers
- Making claims about service/infrastructure status
- Reporting on API state or account connectivity
- Asserting something "is working" or "is down"
- EP AWS accounts, V1 connectivity, Teams polling status
- Any sentence pattern: "X is [state]" about external systems

## Verification
- [ ] Hook fires in original scenario
- [ ] Hook produces intended behavior change
- [ ] No critical workflows broken
- Monitoring period: 2 weeks
- Monitoring started: 2026-04-19
- Last verified: —
