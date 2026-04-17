# DATA-POLICY.md — Channel Data Classification Rules

_Effective: 2025-07-14 | Owner: Joel Ginsberg | Enforced by: Coconut_

## Purpose

Define what content is allowed in each communication channel to prevent customer-sensitive data from leaking into personal or insecure platforms.

---

## Data Classification

| Level | Description | Examples |
|-------|-------------|----------|
| **PUBLIC** | Non-sensitive, general knowledge | Product docs, public URLs, general Trend Micro info |
| **INTERNAL** | Squad coordination, non-sensitive | Meeting times, task assignments, skill progress, config changes |
| **CUSTOMER** | Customer-identifiable or account-specific | Customer names, case numbers, PII, account intel, MDR alerts, meeting transcripts |
| **PERSONAL** | Joel's personal projects, non-work | Side projects, personal dev, unrelated automation |

---

## Channel Rules

### Teams — Squad Chat (Private)
- ✅ PUBLIC, INTERNAL, CUSTOMER
- ❌ PERSONAL
- **Purpose:** Primary channel for customer data, cases, account intel, meeting notes
- **Rationale:** Corporate-managed, compliant, manager-approved channel

### Slack — #all-misfits
- ✅ PUBLIC, INTERNAL
- ⚠️ CUSTOMER — **Limited.** General account references OK (e.g., "EP meeting went well"). No PII, case numbers, customer emails, or sensitive account details.
- ❌ PERSONAL
- **Rationale:** Joel's personal Slack workspace — not enterprise-managed. Keep customer specifics in Teams.

### Slack — #coco-chat
- ✅ PUBLIC, INTERNAL
- ❌ CUSTOMER, PERSONAL
- **Purpose:** Coconut infrastructure, polling status, skill progress, config changes
- **Rationale:** Technical plumbing channel — no customer data belongs here

### Slack — #social
- ✅ PUBLIC
- ❌ INTERNAL, CUSTOMER, PERSONAL
- **Purpose:** Casual, social, vibes only
- **Rationale:** Keep it fun and clean

### Slack — Joel DM
- ✅ PUBLIC, INTERNAL
- ⚠️ CUSTOMER — **Limited.** Urgent flags only, same rules as #all-misfits
- ✅ PERSONAL (Joel-only context)
- **Rationale:** Private channel with primary operator

### GitHub — joel-ginsberg repos
- ✅ PUBLIC, INTERNAL (technical)
- ❌ CUSTOMER (no PII, case numbers, customer emails in code/issues/PRs)
- ❌ PERSONAL (unless personal repos are separated)
- **Rationale:** Public-facing or semi-public repos — no customer data

### Web UI
- ✅ ALL (private session with Joel)
- **Rationale:** Local, not transmitted. Full access for all work.

---

## Decision Audit Logging

Every outbound message from Coconut that involves data classification judgment is logged to `memory/audit-log.md` with:

- **Timestamp** (ISO 8601)
- **Channel** where content was posted
- **Classification** of the data involved
- **Decision** — what was included/excluded
- **Why** — reasoning for the decision

### What triggers an audit entry:
- Posting customer-related information to any channel
- Choosing NOT to include customer data (and redirecting to Teams instead)
- Any edge case where classification is ambiguous

### What does NOT need an audit entry:
- Routine internal/technical messages (skill updates, config changes)
- Social/casual messages
- Direct responses to questions with no data classification ambiguity

---

## Enforcement

- Coconut checks this policy before posting to any channel
- If unsure about classification → default to the MORE restrictive option
- If customer data needs to reach a non-Teams channel → ask Joel first
- All policy violations are self-reported in the audit log
- Policy changes require Joel's approval and are tracked in git

---

## Review

- Joel reviews audit log periodically (or on demand)
- Policy updated as new channels or accounts are added
- Git history provides full rollback capability

---

_Created by Coconut with Joel's approval. Last updated: 2025-07-14_
