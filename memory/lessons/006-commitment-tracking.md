# Lesson 006: Track Commitments Like Tasks

## Date
2026-04-26

## Source
Joel called out that I said "I'll test and check back in at 1pm" about the comms preprocessor and never followed through. Metacognition didn't flag it either.

## What Happened
- On 2026-04-25 I told Joel I'd test the preprocessor and check back at 1 PM
- I never tested it. I never checked back.
- The metacognition system ran 7+ times between then and Joel catching it
- Not a single module flagged the broken commitment
- Joel had to ask about it 15+ hours later

## Root Cause
The metacognition system has ZERO capability to track commitments. None of the modules scan for promise language ("I'll", "I will", "by X time", "check back"). The pattern-detector looks for circular rebuilds and repeated errors. The self-audit checks infrastructure health. The lesson-review checks lesson implementation. Nobody watches for "did I do what I said I'd do?"

This is the same "promise then drift" pattern flagged in metacognition on 2026-04-23. Pattern was identified, never mechanically fixed.

## Lesson/Principle
**Every commitment made in chat is a task.** If you say "I'll do X by Y", that's a binding commitment that needs tracking, not a casual remark. Metacognition must scan for and track these automatically — relying on behavioral discipline alone has failed repeatedly.

## Fix
Build a `commitment-tracker` metacognition module that:
1. Scans recent outbound messages for commitment language
2. Extracts the commitment + deadline
3. Records in a commitments file
4. On each metacog run, checks unfulfilled commitments past deadline
5. Alerts via Slack if a commitment is overdue

## Hook Status
new — building now

## Verification
- [ ] Module created and registered in modules.yaml
- [ ] Test with historical commitment ("check back at 1pm")
- [ ] Verify it would have caught this specific miss
