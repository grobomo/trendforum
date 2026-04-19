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
