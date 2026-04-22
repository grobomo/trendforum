# Teams Chat Access Policy

> Established 2026-04-22 per Joel's directive. Enforcement via config defaults + future hook module.

## Default Access Rules

| Chat Type | Default Access | Override |
|-----------|---------------|----------|
| **DM (1:1)** | `disabled` | Opt-in only — must be explicitly added with `access: read-write` or `read-only` |
| **Group chat** | `read-only` | Opt-out — monitored unless explicitly set to `disabled` |
| **Coconut-created chat** | `read-write` | Auto-granted — any chat Coconut creates gets read-write by default |
| **Write access (any chat)** | Never auto-granted | Always opt-in — must be explicitly set to `read-write` in config |

## How It Works

### DMs (1:1 chats)
- **Never monitored unless explicitly opted in.** Joel's private conversations are his.
- A DM only appears in polling if someone manually adds it to `config.json` with `access: read-write` or `read-only`.
- Auto-discovered DMs are ignored entirely (not even added to config).

### Group Chats
- **Monitored (read-only) by default.** Coconut can see what's happening but won't post.
- To disable monitoring: set `access: disabled` in config.
- To enable replies: set `access: read-write` in config (explicit opt-in).

### Coconut-Created Chats
- When Coconut creates a new group chat (e.g., "Joel + Coconut + X"), it auto-adds the chat to config with `access: read-write`.
- This is the only case where write access is granted automatically.

### Write Access
- **Always explicit.** No auto-discovery, no inference, no default.
- Must be manually set to `read-write` in `config.json`.

## Chat Type Detection

Teams chat IDs follow patterns:
- **DM (1:1):** `19:<uuid>_<uuid>@unq.gbl.spaces`
- **Group chat:** `19:<hex>@thread.v2`
- **Meeting chat:** `19:meeting_<base64>@thread.v2`

The service uses these patterns to apply the correct default.

## Auto-Discovery Behavior

When the service discovers a new chat (via Graph API `/me/chats`):
1. Detect chat type from ID pattern
2. Apply default access per this policy
3. **DMs → skip entirely** (don't add to config)
4. **Group/meeting chats → add as `read-only`** with `section: auto-discovered`
5. **Never auto-grant `read-write`**
6. Log the discovery for audit

## Data Leakage Prevention (DLP)

This policy is the first layer of a broader DLP framework. Future hook modules will enforce:

1. **Access policy enforcement** — reject writes to non-read-write chats at the API layer (not just config check)
2. **Content filtering** — prevent leaking data from one chat context into another (ghost trigger / context bleed prevention)
3. **PII/credential scanning** — block outbound messages containing API keys, tokens, passwords
4. **Cross-chat isolation** — ensure compose context never bleeds between chat sessions
5. **Audit logging** — log every outbound message with source chat, target chat, and content hash

### Hook Module: `teams-access-guard`

**Status:** Planned — needs implementation as OpenClaw hook-runner module.

**Enforcement points:**
- Pre-send hook: validate `access: read-write` before any Graph API POST
- Pre-compose hook: verify chat context isolation (no cross-chat bleed)
- Post-discover hook: apply default access policy to newly discovered chats
- Audit hook: log all outbound messages for compliance review

**Priority:** High — current enforcement is config-based only (software guard, not hardware guard). A bug in compose logic could bypass it.

---

_Policy owner: Joel Ginsberg_
_Enforced by: teams_service.py (config-based) + teams-access-guard hook module (planned)_
_Last updated: 2026-04-22_
