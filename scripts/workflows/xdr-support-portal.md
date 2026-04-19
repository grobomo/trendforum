# XDR Support Portal — Workflow Pseudocode

## Prerequisites
- VPN connected (F5 BIG-IP Edge Client → vpn.trendmicro.com)
- Chrome running with Blueprint MCP extension
- Blueprint MCP server started in mcp-manager

## Workflow 1: VPN Connect
```
1. CHECK vpn status via f5fpc -info (Windows Python)
   - code 1 → already connected, skip
   - code 0/64 → disconnected, proceed
   - code 16 → user attention required, reset + proceed
2. RESET vpn-monitor stopped state (--reset flag)
3. RUN vpn_reconnect.py (Windows Python)
   - Script handles: stop F5 processes → f5fpc -start → SSO login
   - Script auto-fills email (joel_ginsberg@trendmicro.com)
   - Script detects MFA number, emails it to Joel
   - Joel approves on Authenticator app
   - Script waits up to 120s for connection
4. VERIFY f5fpc -info returns code 1 (Connected)
```

## Workflow 2: XDR Support Portal Login
```
1. NAVIGATE to https://support.xdr.trendmicro.com/#/admin/products
2. WAIT for page load → login form appears
3. CLICK button.login-form-button ("Log On with Domain Credentials")
4. WAIT for redirect → "Sign in with your corporate ID" page
5. CLICK [data-value] button containing "AAD" text
   - Selector: button with text "AAD" or similar corporate SSO button
6. WAIT for redirect → Microsoft SSO page
   - May land on "Face, fingerprint, PIN or security key" (Windows Hello)
   - If so: CLICK "Back" button (#idBtn_Back) to get alternative methods
7. ON "Verify your identity" page:
   - CLICK [data-value="PhoneAppNotification"] ("Approve a request on my Microsoft Authenticator app")
8. WAIT for "Approve sign in request" page → shows 2-digit number
9. EXTRACT MFA number from page (large number display)
10. NOTIFY user with MFA number (via Slack/Teams)
11. WAIT for approval → page redirects to portal
12. VERIFY URL contains support.xdr.trendmicro.com/#/admin
```

## Workflow 3: Search Customer
```
1. LOCATE search input: input[placeholder*="Company"]
2. CLEAR any existing text
3. TYPE customer name (min 3 characters)
4. PRESS Enter or CLICK search icon (.ant-input-search-icon)
5. WAIT for table results (.ant-table-body tr)
6. VERIFY customer appears in results
7. EXTRACT row data: Company, Company ID, Trend Micro Account, Region
```

## Workflow 4: Open Customer XDR Console
```
1. CLICK gear icon (.anticon-setting) in Action column of target customer row
2. WAIT for "Open XDR Console" modal dialog
3. FILL form:
   a. Case ID type: select from dropdown (JIRA default)
   b. Case ID value: type case number in text input
   c. Role: select "Technical Support" (default)
   d. Comments: type reason for access
4. CLICK submit/confirm button
5. WAIT for V1 console to open (new tab or redirect)
6. VERIFY V1 console loaded for correct customer tenant
```

## Workflow 5: Check Policy Events (in V1 Console)
```
1. IN V1 console, navigate to: XDR > Search
   - Or: Threat Intelligence > Suspicious Object List > Policy Events
   - Or: Email Security section depending on what we're checking
2. SET time range filter (e.g., last 7 days)
3. SEARCH for relevant events:
   - Email policy events (missed/blocked/quarantined)
   - Filter by sender/recipient/subject as needed
4. EXTRACT results: timestamp, event type, action taken, details
5. EXPORT or screenshot findings
```

## Key Selectors Reference
```
Login page:
  - Login button: button.login-form-button
  - AAD SSO: button with "AAD" text in corporate ID page

Microsoft SSO:
  - Back button: #idBtn_Back
  - Authenticator option: [data-value="PhoneAppNotification"]
  - MFA number: large text element on approval page

Portal:
  - Search input: input[placeholder*="Company"]
  - Clear search: .ant-input-clear-icon
  - Search icon: .ant-input-search-icon
  - Table rows: .ant-table-body tr
  - Gear icon: .anticon-setting
  - Close drawer: .ant-drawer-close

Open Console modal:
  - Case ID dropdown: TBD (ant-select)
  - Case ID input: TBD
  - Role dropdown: TBD (ant-select)  
  - Comments textarea: textarea[placeholder*="explain"]
  - Submit button: TBD
```

## Notes
- Windows Hello prompt cannot be automated from WSL — must use "Back" to reach Authenticator flow
- AAD SSO page at xdr-slog-ue1-kibana.auth.us-east-1.amazonaws.com handles the corporate ID selection
- Microsoft login at login.microsoftonline.com handles MFA
- support.xdr.trendmicro.com resolves to internal AWS ELB (10.133.x.x) — VPN required
- Blueprint MCP server needs timeout: 60000 in config (Windows FS slow from WSL)
- Sharp module needs linux-x64 variant installed for screenshots
