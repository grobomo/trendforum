# Audit Log — Data Classification Decisions

_Format: ISO timestamp | Channel | Classification | Decision | Why_

---

## 2025-07-14

- **2025-07-14T19:30:00-05:00** | Teams (private) | INTERNAL | Posted DATA-POLICY.md summary | Joel requested channel data rules — Teams is approved for all squad content including customer data. No classification risk.

---

_Entries added by Coconut. Git-tracked for rollback._

## 2026-04-18T04:35:00Z — EP Cloud Account Data in Slack (VIOLATION + CORRECTION)
- **Channel:** Slack DM (D0ATWPM4DTK)
- **Classification:** CUSTOMER
- **Decision:** POSTED customer AWS account IDs and resource counts to Slack DM — VIOLATION of DATA-POLICY.md
- **Correction:** Immediately deleted the Slack message (1776487009.957259) upon Joel's warning, then reposted to Teams Coconut Private chat (compliant channel)
- **Why:** Mistake — treated Slack DM as safe for customer data. DATA-POLICY says Slack DM is "Limited" for CUSTOMER data (urgent flags only, no sensitive account details). AWS account IDs and detailed resource breakdowns qualify as sensitive account details. Lesson learned.

## 2026-04-19T05:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** No channel had a `policy-summary.md` in its `_shared/` directory. The compose pipeline loads only its channel's memory files — without a local policy reference, DATA-POLICY.md rules were not surfaced at compose time. This is structural drift: the policy exists centrally but was absent from the per-channel memory where it's actually needed.
- **Correction:** Created `policy-summary.md` in all 5 channel `_shared/` directories, each documenting allowed/prohibited data classifications per DATA-POLICY.md, plus channel-specific notes and incident references.
- **Audit log review:** Two prior entries (2025-07-14 initial setup, 2026-04-18 Slack DM violation). No new drift indicators beyond the missing policy files.
- **Status:** All channels now have local policy summaries. Next audit should verify these remain in sync with DATA-POLICY.md.

## 2026-04-19T19:14:00Z — Customer Data in #all-misfits (VIOLATION + CORRECTION)
- **Channel:** Slack #all-misfits (C0ATFDQRGRL)
- **Classification:** CUSTOMER
- **Decision:** POSTED customer-specific data in squad task board update — VIOLATION of DATA-POLICY.md
- **What leaked:**
  - Message 1 (task board): Customer name (EP) + contact name (Dan Toresi) + specific count ("46 AWS accounts") + technical detail (CFN stack updates). Also: Panavision + contact (Matt Patterson) + phishing report details. Dole case numbers (TM-03941209, TM-03943850).
  - Message 2 (Monday prep): Company 3 + Robert Romero by name + specific infrastructure details (scanner on port 80, no TLS, no API key)
- **Correction:** Both messages deleted immediately upon Joel's flag. No replacement posted — will repost sanitized versions.
- **Root cause:** Policy-summary.md files exist but aren't enforced programmatically. I composed a status update listing every tracked item with full customer context, which is fine for Teams but violates #all-misfits CUSTOMER rules ("general account references OK, no PII, case numbers, or sensitive details").
- **Joel's directive:** Need pre-tool-use blocking hook modules to enforce comms policies before messages reach channels. Software guardrails > discipline.
- **Lesson:** This is the SECOND EP data leak in Slack in 2 days. Pattern = structural, not carelessness. Confirms Joel's point: need automated enforcement, not just policy docs.

## 2026-04-19T17:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 channel `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit.
- **Observation:** `#coco-metacognition` Slack channel (in TOOLS.md) is not listed in DATA-POLICY.md. Would logically follow #coco-chat rules. Flag for Joel's next policy review.
- **Corrections:** None required.
- **Status:** No drift detected. Next audit scheduled per cron.

## 2026-04-19T23:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** Slack `_shared/policy-summary.md` was missing the 2026-04-19 #all-misfits CUSTOMER violation (customer names, contact names, case numbers, infrastructure details in two messages — both deleted). This incident occurred at 19:14 UTC, after the prior 17:00 UTC audit, so the policy-summary was stale.
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` appear in TOOLS.md but have no DATA-POLICY.md entries. Previously flagged for `#coco-metacognition` only — expanding flag to all four. Suggest Joel add these to DATA-POLICY.md at next review.
- **Correction:** Updated Slack `_shared/policy-summary.md` Incidents section to include the 2026-04-19 #all-misfits violation.
- **Status:** All 5 policy-summary.md files present and core classification rules in sync. One correction made (incident backfill). Four uncovered Slack channels flagged for Joel's policy review.

## 2026-04-19T23:46:18Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🟡 Graph API env vars (MSGRAPH_TENANT_ID/CLIENT_ID) not set in this context.
*Exposed Ports:*
  • 🟡 Unexpected port *43931* listening on non-loopback: `100.120.65.116:43931` (unknown)
  • 🟡 Unexpected port *3000* listening on non-loopback: `0.0.0.0:3000` (users:(("MainThread",pid=38901,fd=21)))
  • 🟡 Unexpected port *443* listening on non-loopback: `100.120.65.116:443` (unknown)
  • 🟡 Unexpected port *8443* listening on non-loopback: `100.120.65.116:8443` (unknown)
  • 🟡 Unexpected port *53* listening on non-loopback: `10.255.255.254:53` (unknown)
  • 🟡 Unexpected port *631* listening on non-loopback: `0.0.0.0:631` (unknown)
  • 🟡 Unexpected port *8443* listening on non-loopback: `[fd7a:115c:a1e0::7136:4174]:8443` (unknown)
  • 🟡 Unexpected port *443* listening on non-loopback: `[fd7a:115c:a1e0::7136:4174]:443` (unknown)
  • 🟡 Unexpected port *35665* listening on non-loopback: `[fd7a:115c:a1e0::7136:4174]:35665` (unknown)
  • 🟡 Unexpected port *8080* listening on non-loopback: `[::ffff:127.0.0.1]:8080` (users:(("signal-cli",pid=71922,fd=7)))
  • 🟡 Unexpected port *631* listening on non-loopback: `[::]:631` (unknown)
*File Permissions:*
  • 🔴 `.openclaw/openclaw.json` is world-readable (mode 664). Fix: `chmod o-r /home/ubu/.openclaw/openclaw.json`
  • 🔴 `.openclaw/workspace/scripts/poll_all.py` is world-readable (mode 664). Fix: `chmod o-r /home/ubu/.openclaw/workspace/scripts/poll_all.py`
  • 🔴 `.openclaw/workspace/scripts/entra-cred-store.py` is world-readable (mode 775). Fix: `chmod o-r /home/ubu/.openclaw/workspace/scripts/entra-cred-store.py`
*Plugin Integrity:*
  • ℹ️ First run — baseline recorded for 6 plugin files.

## 2026-04-19T23:46:59Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🟡 Graph API env vars (MSGRAPH_TENANT_ID/CLIENT_ID) not set in this context.
*Exposed Ports:*
  • 🟡 Unexpected port *43931* listening on non-loopback: `100.120.65.116:43931` (unknown)
  • 🟡 Unexpected port *35665* listening on non-loopback: `[fd7a:115c:a1e0::7136:4174]:35665` (unknown)

## 2026-04-19T23:47:14Z — Security Audit (cron)
- *Findings:*
*Exposed Ports:*
  • 🟡 Unexpected port *43931* listening on non-loopback: `100.120.65.116:43931` (unknown)
  • 🟡 Unexpected port *35665* listening on non-loopback: `[fd7a:115c:a1e0::7136:4174]:35665` (unknown)

## 2026-04-19T23:47:54Z — Security Audit (cron)
- Audits: Credential Expiry, Exposed Ports, File Permissions, Plugin Integrity — all clean.

## 2026-04-20T05:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-19T23:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-20T13:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-20T05:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-20T17:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-20T13:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-20T23:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-20T17:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-21T05:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-20T23:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-20T11:00:08Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🔴 Trello API credentials missing from keyring.
  • 🟡 V1_API_KEY missing from keyring (may not be needed).

## 2026-04-21T13:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-21T05:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-21T23:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-21T13:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-21T11:00:08Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🔴 Trello API credentials missing from keyring.
  • 🟡 V1_API_KEY missing from keyring (may not be needed).
*Exposed Ports:*
  • 🟡 Unexpected port *8445* listening on non-loopback: `0.0.0.0:8445` (users:(("python3",pid=127369,fd=3)))

## 2026-04-22T05:01:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-21T23:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-22T13:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-22T05:01Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-22T11:00:10Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🔴 Trello API credentials missing from keyring.
  • 🟡 V1_API_KEY missing from keyring (may not be needed).
*Exposed Ports:*
  • 🟡 Unexpected port *8445* listening on non-loopback: `0.0.0.0:8445` (users:(("python3",pid=22223,fd=3)))
*File Permissions:*
  • 🔴 Plugin `index.ts` in `mfa-skill-guard` is world-writable (mode 777)
  • 🔴 Plugin `test.ts` in `mfa-skill-guard` is world-writable (mode 777)
*Plugin Integrity:*
  • ℹ️ New plugin file: `mfa-skill-guard/config.example.json`
  • ℹ️ New plugin file: `mfa-skill-guard/index.ts`
  • ℹ️ New plugin file: `mfa-skill-guard/openclaw.plugin.json`
  • ℹ️ New plugin file: `mfa-skill-guard/package.json`
  • ℹ️ New plugin file: `mfa-skill-guard/test.ts`

## 2026-04-22T17:11:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-22T13:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-22T23:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-22T17:11Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-23T05:00:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-22T23:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-23T11:00:09Z — Security Audit (cron)
- *Findings:*
*Credential Expiry:*
  • 🔴 Trello API credentials missing from keyring.
  • 🟡 V1_API_KEY missing from keyring (may not be needed).
*Exposed Ports:*
  • 🟡 Unexpected port *8445* listening on non-loopback: `0.0.0.0:8445` (users:(("python3",pid=465,fd=3)))
*File Permissions:*
  • 🔴 Plugin `index.ts` in `mfa-skill-guard` is world-writable (mode 777)
  • 🔴 Plugin `test.ts` in `mfa-skill-guard` is world-writable (mode 777)

## 2026-04-23T16:31:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-23T05:00Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.

## 2026-04-23T17:01:00Z — Scheduled Comm Policy Audit (cron)
- **Scope:** All 5 channels (teams, slack, email, github, trello)
- **Finding:** All clean. All 5 `_shared/policy-summary.md` files present and in sync with DATA-POLICY.md (last updated 2026-04-18). No new violations or edge-case entries since prior audit (2026-04-23T16:31Z).
- **Observation (carried forward):** Slack channels `#coco-metacognition`, `#cdt-imsva-analyzer`, `#son`, `#scheduling` still lack DATA-POLICY.md entries. Flagged since 2026-04-19 — awaiting Joel's policy review.
- **Corrections:** None required.
- **Status:** No drift detected. All channels compliant.
