# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### Trello

- Board: To Do List (`TyFBN1Bx`) — <https://trello.com/b/TyFBN1Bx/to-do-list>
- Lists:
  - `6954d3af836b51597afff8e9` = Coconut Todo (my tasks)
  - `6954d3af836b51597afff8e8` = Joel Todo
  - `69e19cd7864480d809461861` = Justin Todo
  - `69e19cce3a6e1e41e5c910e6` = Chrissa Todo
  - `6954d3af836b51597afff8f1` = Done
- API creds in Linux keyring: `openclaw/TRELLO_API_KEY`, `openclaw/TRELLO_TOKEN`
- Mark cards `dueComplete: true` → Trello automation moves to Done list
- API: `https://api.trello.com/1/` with `key` + `token` params

### Slack

- Joel's user ID: `U0ATB4AAGJF`
- Joel's DM channel: `D0ATWPM4DTK`
- Bot user ID: `U0ATFQQ4WNS`
- Bot name: Coconut
- Workspace: misfits-rtf1993

---

Add whatever helps you do your job. This is your cheat sheet.
