# Lesson: Automate Everything — Never Rely on Yourself to Do Anything

## Observation
2026-04-24: Joel pointed out the Trello board isn't getting automatic updates from Claude Code tabs. The tracking system I built (manage.py) relies on ME calling it at the right time — during heartbeats, when I remember, when I notice. That's the helpdesk-tech pattern again. If I have to remember to do something, it won't happen reliably.

## The Principle
**Never rely on yourself (or any AI) to remember to do something.** Automate it or it won't happen.

This applies to:
- **Trello updates:** Don't rely on Coconut to manually call manage.py. Wire it into hooks, crons, and scripts that fire automatically.
- **Claude Code monitoring:** Don't rely on heartbeat checks. Wire checkins into the stop hook so they fire automatically on every task completion.
- **Status tracking:** Don't rely on memory or session state. Write to durable files/APIs that persist across sessions.
- **Verification:** Don't rely on me to verify work. Build verification into the close script.

## Anti-Patterns (things I keep doing)
1. **"I'll check during the next heartbeat"** — Heartbeats are 15 min apart and I might be busy. Wire it into a hook or cron instead.
2. **"I'll update Trello after I verify"** — I'll forget, or the session will compact. Make the update happen in the same script that does the work.
3. **"I'll track this in my daily notes"** — Daily notes are for me. Trello is for Joel. Update both, or better yet, update Trello and let Trello be the source.
4. **Building systems that require me to be the glue** — If a system only works when I'm actively orchestrating it, it's not a system, it's a manual process with extra steps.

## The Fix Pattern
For anything that needs to happen reliably:
1. Can it be a **hook module** (before/after tool call)? → Build a hook.
2. Can it be a **cron job**? → Build a cron.
3. Can it be a **GitHub Action** (on push/PR)? → Build a workflow.
4. Can it be **embedded in the script that triggers it**? → Add it to that script.
5. Only if none of the above: rely on heartbeat polling (last resort).

Humans are unreliable. AIs are worse — we lose memory every session. The only reliable actor is code that runs on a trigger.

## Specific Fixes Needed
- Claude Code tab tracking: manage.py should be called BY the stop hook / new_session.py, not by me in heartbeats
- Trello card updates: openclaw-checkin.py should update Trello directly, not route through my session
- Tab close + card complete: should be automated when Claude Code's TODO.md is fully checked

## Source
- Joel: "Need to automate everything don't rely on yourself to do anything"
- Conversation: 2026-04-24
- Related: "Think like an IT admin, not a helpdesk tech" (MEMORY.md)
- Related: "chips-in-a-bowl" principle — hooks block, instructions don't

## Retrieval Triggers
- Building any tracking or monitoring system
- "I'll check later", "I'll update during heartbeat"
- Manual process, rely on self, remember to
- Trello not updating, board out of date
- Automation vs manual
