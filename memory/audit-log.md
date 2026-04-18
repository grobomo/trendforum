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
