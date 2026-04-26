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
  - `69ed8859098694a1dabe4e2b` = Researching (cards being researched before spec/build)
  - `69e81730d4333e58a9aa2d0e` = Joel Next Steps
  - `6954d3af836b51597afff8e8` = Joel Todo
  - `69e8173131921413c149f962` = Justin Next Steps
  - `69e19cd7864480d809461861` = Justin Todo
  - `69e81731fc65aa3403256ac3` = Chrissa Next Steps
  - `69e19cce3a6e1e41e5c910e6` = Chrissa Todo
  - `69e51fe0ad60dd711d6e9fcc` = Testing
  - `69ebe51d36d2269f7c93de8c` = Claude Code Tabs
  - `6954d3af836b51597afff8f1` = Done
- API creds in Linux keyring: `openclaw/TRELLO_API_KEY`, `openclaw/TRELLO_TOKEN`
- Mark cards `dueComplete: true` → Trello automation moves to Done list
- API: `https://api.trello.com/1/` with `key` + `token` params

### Gate & Metacog Tracker Board
- Board: Gate & Metacog Tracker (`iBDjKzko`) — <https://trello.com/b/iBDjKzko/gate-metacog-tracker>
- Workspace: Customers (claude16)
- Lists:
  - `69edce6ef823ede97ad98faa` = 📋 New
  - `69edce6f105866c730c068d6` = 📝 Log-only
  - `69edce6f10236b61ca96e6a3` = 🔒 Enforcing
  - `69edce6fc38abac70bcda5ee` = 🛡️ Trusted
  - `69edce70088f8500a1424b40` = Metacog Modules
- Flow: New → Log-only → Enforcing → Trusted (🔑 MFA at each transition)
- Gate cards move between lists as they progress through lifecycle
- Metacog module cards stay in their list (tracked for visibility)

### Lessons Board
- Board: Coconut Lessons (`bZudEKUZ`) — <https://trello.com/b/bZudEKUZ/coconut-lessons>
- Workspace: Customers (claude16)
- Lists:
  - `69e3e694635b28132b1ab3e9` = Inbox (new lessons land here)
  - `69e3e694fe89c3d1e8e1f274` = Technical & Tooling
  - `69e3e69392ec78a4b39e9912` = Process & Communication
  - `69e3e6939485549f08235d0c` = Customer & Accounts
  - `69e3e693800309fd278f4b22` = Applied (lessons fully integrated)
- Labels: ✅ Applied (green), ⚠️ In Progress (yellow), 🔥 Learned the Hard Way (red), 💡 Insight (blue), 🔄 Recurring (purple)
- Flow: new lessons → Inbox → categorize into appropriate list → mark Applied when integrated

### DD Lab Board
- Board: DD Lab - Task Tracker (`ado3MGo4`) — <https://trello.com/b/ado3MGo4/dd-lab-task-tracker>
- Workspace: Customers (claude16)
- Lists:
  - `69e3f790c605b0736d9264bf` = Backlog
  - `69e3f790520cb07a5e338c08` = In Progress
  - `69e3f791bc7c408f8104ac14` = Done
  - `69e3f791e29f36119f4366b0` = Blocked
- Created by: Claude Code (dd-lab project) via Coconut, 2026-07-16

### DD Lab Board
- Board: DD Lab - Task Tracker (`rM80Xd99`) — <https://trello.com/b/rM80Xd99/dd-lab-task-tracker>
- Workspace: Customers (claude16)
- Lists:
  - `69e3faeed32edeb063687593` = Backlog
  - `69e3faee0c5abdb222eaa94f` = In Progress
  - `69e3faefcf5c263647f407a1` = Done
  - `69e3faef18cadcc51344722a` = Blocked
- Created by: Claude Code (dd-lab project) via Coconut, 2026-07-16

### Comm Tracking Board
- Board: Comm Tracking (`IOKOO2dU`) — <https://trello.com/b/IOKOO2dU/comm-tracking>
- Workspace: Customers (claude16)
- Lists:
  - `69e3e026902dca6233d719bf` = Channel Status
  - `69e3e026c1800981f471f063` = Active Threads
  - `69e3e02624bfdaee34f2655b` = Missed / Pending
- Cards (Channel Status):
  - `69e3e03b6cd9b22e36f7e441` = 📧 Email
  - `69e3e03b8cf6358ddc0939e5` = 💬 Teams
  - `69e3e03cbba0f57151a5ce5c` = 🔀 GitHub
  - `69e3e03c8ec1f34110747b5d` = 💜 Slack
  - `69e3e03defe4e70a38d0bece` = 📋 Trello
- Source of truth: local `memory/channels/*.md` files
- Trello is the human-facing visibility mirror, updated when possible

### Dynamics 365 CRM (Case Lookup)
- URL: `https://trendmicro.crm.dynamics.com`
- Auth: Joel's MS Entra SSO → MFA required via Authenticator app
- App: Customer Service Workspace (PowerApps-based)
- After login, Dynamics may show "Sign in to continue" popup — click "Sign in" button to proceed
- Known quirk: MFA approval sometimes doesn't stick on first try; may need 2-3 attempts
- Case search: use Global Search bar at top, search by case number (e.g. `TM-03953649`)
- PCT/Jira linked cases: look for "Associated SEG or PCT Case" tab in case view

### MFA Flow (Dynamics / MS Login)
**Goal:** Get Joel's MFA approval code from the browser login screen and relay it to Slack.

**Steps:**
1. Navigate Blueprint browser to target URL (e.g. `trendmicro.crm.dynamics.com`)
2. MS redirects to `login.microsoftonline.com` → MFA prompt renders
3. Take screenshot: `browser_take_screenshot`
4. **Use Haiku** (`model: trendmicro-aiendpoint/claude-4.5-haiku`) to read the 2-digit code from screenshot — fast + cheap
5. Post code to Joel's Slack DM immediately
6. Joel approves on Authenticator app
7. Wait 5-8 seconds, screenshot again to confirm auth succeeded
8. If stuck on "Please sign in again" or "Sign in to continue" → close tab, open fresh one, retry

**Key rules:**
- ALWAYS use Haiku for screenshot → code extraction (Joel's request — Opus is too slow for this)
- Be fast — MFA prompts expire. Don't waste time on DOM snapshots; go straight to screenshot → Haiku → Slack
- Copy screenshots to workspace dir before sending to `image` tool (tmp paths not allowed)

### Blueprint MCP (Browser Automation)
- MCP server: `blueprint-extra` in mcp-manager
- Connects to Chrome extension in Joel's Windows Chrome (Profile 3)
- Extension communicates via WebSocket relay on port 5555
- Gives access to Joel's real browser with all logged-in sessions, cookies, extensions
- Helper script: `scripts/blueprint-connect.sh`
- Server path: `/mnt/c/Users/joelg/Documents/ProjectsCL1/_shared/MCP/blueprint-extra-mcp/run-server.js`
- Config fix: uses `node` (not `C:/nodejs/node.exe`) and timeout: 60000 (Windows FS is slow)
- Key tools: `enable`, `browser_tabs`, `browser_navigate`, `browser_interact`, `browser_snapshot`, `browser_take_screenshot`
- XDR Support Portal: `support.xdr.trendmicro.com` — VPN-only (internal AWS ELB)
- Product Cloud: `bleego.productcloud.trendmicro.com` — VPN-only
- V1 Console: `portal.xdr.trendmicro.com` — public, needs V1 sign-in
- Sharp module: installed linux-x64 variant for screenshot support from WSL

### Slack

- Joel's user ID: `U0ATB4AAGJF`
- Joel's DM channel: `D0ATWPM4DTK`
- Bot user ID: `U0ATFQQ4WNS`
- Bot name: Coconut
- Workspace: misfits-rtf1993

**Channel Routing:**
- `#all-misfits` (`C0ATFDQRGRL`) — customer/business chat. Post account updates, email triages about customers, meeting invites, partner intel. Always respond.
- `#coco-chat` (`C0ATJE19YRY`) — Coconut processes & infrastructure. Post polling status, skill progress, research findings (IronClaw, Hermes, etc.), config changes, technical plumbing. Always respond.
- `#social` (`C0ATB4AS9PD`) — casual/social. Always respond.
- `#coco-metacognition` (`C0ATCRVSB71`) — metacognition channel. Thinking about thinking, making thought processes visible for self-improvement.
- Joel DM (`D0ATWPM4DTK`) — private comms with Joel. Urgent flags, private info, things not for the squad.
  - `#cdt-imsva-analyzer` (`C0ATM9PB59T`) — CDT/IMSVA analyzer development. Always respond.
  - `#son` (`C0ATJVC4LUB`) — TBD purpose. Always respond.
  - `#scheduling` (`C0ATK8YJQD9`) — scheduling channel. Always respond.

**Group Policy:** `open` — auto-monitors any channel Coconut is invited to (no manual config needed).

### Teams Message Styles
- Default style: `island` (Adaptive Card with beach bg + emphasis container)
- Available: `island`, `clean` (green left border HTML), `plain` (raw HTML)
- Style templates: `scripts/teams-poller/styles/` with `STYLES.md` documentation
- `send_direct.py --style <name>` overrides per-message
- Per-chat config: `"style": "island"` in config.json

### Teams — How to Send Messages

**The ONLY way to send a Teams message:**
1. Write your message to a temp file (e.g. `/tmp/teams-reply.txt`)
2. Pipe it to `queue_reply.py`:
   ```
   python3 scripts/teams-poller/queue_reply.py --chat-id "19:abc123@thread.v2" < /tmp/teams-reply.txt
   ```
3. The teams_service daemon picks up the queue and posts via Graph API

**Rules:**
- Message body comes from stdin ONLY (never positional args)
- Use `--chat-id` with the full Teams chat ID, or use `--chat` with a label from config.json
- 🌴 bookends are auto-enforced by queue_reply.py (added if missing), but ALWAYS include them yourself
- Never call Graph API directly, never use send_reply.py directly, never write to outbound_queue.json manually
- For read-only chats: queue_reply.py will block the post automatically

**Chat IDs** are in `scripts/teams-poller/config.json` — look up by label.

**DO NOT:**
- Use heredocs / `cat << EOF | python3 ...` (exec preflight blocks it)
- Call the Graph API directly to send messages
- Write to outbound_queue.json by hand

### SearXNG (Self-hosted Web Search)
- URL: `http://127.0.0.1:8888`
- JSON API: `curl 'http://127.0.0.1:8888/search?q=QUERY&format=json'`
- Helper: `~/searxng-data/search.sh "query" [num_results]`
- Config: `~/searxng-data/settings.yml`
- Service: `systemctl --user status searxng` (auto-starts on boot)
- Engines: Google, DuckDuckGo, Startpage, Bing, Wikipedia, and dozens more
- No API keys needed — self-hosted metasearch
- Use before building anything: research existing projects, read current docs, avoid reinventing wheels

### Graph API Search
- Endpoint: `POST /search/query` with `entityTypes: ["chatMessage"]`
- Searches ALL Teams chats at once (no per-chat pagination needed)
- Supports `queryString` for keyword search
- Returns summaries with keyword highlights
- Use `client.post("/search/query", body={...})` via GraphClient
- Requires valid Graph token (refreshes via TokenManager)
- 2263 chats searched in seconds vs ~100 min brute-force

---

Add whatever helps you do your job. This is your cheat sheet.
