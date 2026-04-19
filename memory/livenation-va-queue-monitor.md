# Live Nation — VA Queue Monitoring via XDR Data Query

## Source
Haigui Chen (RD-NA) — Jan 30, 2026 in Teams

## Instructions from Haigui

### Step 1: Create Saved Search in XDR Data Explorer
- Data source: **Email**
- Search query:
  ```
  productCode:sca AND eventName:EMAIL_TRACKING AND scanType:exo_inline_realtime_accepted_mail_traffic AND mailRecipientIp:none
  ```
- Save the query as: **CECP-Queue-Email**

### Step 2: Open Saved Search
- Open the saved search
- (Haigui mentioned no threshold definition — if even one email matches, it indicates VA queue issue)

## Context
- Live Nation CECP (Cloud Email & Collaboration Protection) has recurring VA (Virtual Analyzer) queue issues
- Emails get stuck in inline VA scanning, causing delivery delays
- The query filters for emails that went through inline realtime scanning but have no recipient IP (indicating they're stuck/queued)
- `scanType:exo_inline_realtime_accepted_mail_traffic` = Exchange Online inline scanning
- `mailRecipientIp:none` = email hasn't been delivered yet (no recipient IP recorded)

## Related
- TrendAI Technical Explanation Document: CECP VA Queue - Live Nation (Jan 27, 2026)
- Joel found 5592 emails in VA queue (Jan 29)
- Jonn Perez (TS-NA) drafted the technical explanation doc
- Jing Liu (RD-NA) and Ricardo Ramos (PM-NA) reviewed

## Wednesday Meeting Prep
- [ ] Test this query in V1 XDR Data Explorer (needs valid V1 API token or console access)
- [ ] Check if the saved search can be automated as an alert/notification
- [ ] Determine current VA queue depth for Live Nation
- [ ] Prepare update on queue monitoring fix status
