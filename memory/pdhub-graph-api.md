# PDHUB — Generic Personal Data Hub

## What It Is
Trend InfoSec's pre-scoped, pre-configured Azure AD application for POC use with Microsoft Graph API.
- Portal: `pdhub.infosec.trendmicro.com` (company network required)
- Documented by: Aaron Hsieh (Wiki Cloud page: "Generic Personal Data Hub - Microsoft Graph API Integration Framework")
- Source: Michael Fu (UX-AS), AI IDE/Agent Master Group, 2026-01-30

## How To Use
1. Go to `pdhub.infosec.trendmicro.com`
2. Generate a 15-day limited secret key
3. Get tenant ID + application ID from portal
4. Use those creds + personal MS Graph token (web auth)

```bash
export GPDH_TENANT_ID="your-tenant-id"
export GPDH_APPLICATION_ID="your-application-id"
export GPDH_SECRET_KEY="your-secret-key"
```

## Michael Fu's Library
- Repo: `trend-aatf-external/msgraph-api-typescript-library` (GitHub)
- TypeScript wrapper using PDHUB's pre-scoped app
- Capabilities: Email, Meeting transcripts/recordings, AI meeting insights, Jira, Confluence, Figma
- Has SKILL.md and CLAUDE.md for agent integration

## Key Delegated Permissions (via PDHUB app)
- Mail.Read, Mail.ReadWrite, Mail.Send
- Chat.Read, Chat.ReadWrite
- Calendars.ReadWrite
- OnlineMeetingAiInsight.Read.All (requires admin consent, already granted)
- User.Read

## Meeting Transcript Workaround (Non-Organizer Access)
- Problem: `/me/onlineMeetings` only returns meetings you organized
- Fix: Silently accept calendar event → Graph recognizes you as attendee → transcript/recording access unlocked
- Implementation: `unlockMeetingAccess()` with exponential backoff (2s-10s, 60s timeout)
- Uses `sendResponse: false` so organizer isn't notified

## AI Meeting Insights
Available insight types: summary, actionItem, keyPoint, topic, decision, followUp
Requires: OnlineMeetingAiInsight.Read.All scope + meeting transcription enabled

## IRM / MIP Email Decryption

**Key finding: Graph API CANNOT decrypt IRM/MIP-protected emails directly.**

- 23% of mailbox traffic at Trend is protected by Purview sensitivity labels (Azure RMS)
- Graph API returns the encrypted blob — can't strip protection
- Outlook label change works because Outlook has IRM decryption client, but can't be automated
- Graph API has NO sensitivity label manipulation on messages

**Michael Fu's proposed workaround (Mar 20, 2026):**
- Use MIP SDK to request decryption from Azure RMS (same mechanism Outlook uses)
- Requires `Content.DelegatedReaderPrecedent` scope + admin consent
- Precedent: CAS/TMCASP already has Azure RMS permissions

**PDHub extension has MIP decryption built in:**
- Listed as advanced feature on Claude Desktop via PDHub extension
- Confirmed by Secura bot: "supports advanced features like MIP email decryption"
- Built by CISO Office / Aaron Hsieh's team

**Wiki link (partial):**
`trendmicro.atlassian.net/wiki/spaces/~70121e9fd822cebbd45eda7e2d2a569888643/pages/149127694...`

Source: Michael Fu (UX-AS), AI IDE/Agent Master Group + AI Explorers Hub, cross-chat search 2026-04-18

## Key People
- **Michael Fu (UX-AS)** — built the TypeScript library, expert on Graph API workarounds
- **Aaron Hsieh** — documented PDHUB setup on Wiki Cloud

---
_Discovered: 2026-04-18, from AI IDE/Agent Master Group chat history_
