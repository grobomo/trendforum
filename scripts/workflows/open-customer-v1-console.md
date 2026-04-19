# Open Customer V1 Console — Blueprint Workflow

## Trigger Conditions
- **Keyword triggers:** "customer", "console", "v1", "open console", "support portal", "check [customer]", "log into [customer]"
- **Auto-trigger:** When Blueprint detects navigation to `support.xdr.trendmicro.com`
- **Input processing:** Use Haiku to extract: customer name, reason for login (2-5 words)

## Parameters
- `customerName` — extracted from user request or conversation context
- `reason` — dynamic, brief (2-5 words), e.g. "Check email policy events", "Review endpoint alerts", "Verify cloud accounts"
- `caseType` — always "Salesforce" (default)
- `caseId` — always "11111111" (placeholder)
- `role` — always "Technical Support" (default)

---

## Workflow Steps

### Step 1: VPN Check
```
IF f5fpc -info != connected (code 1):
  RUN vpn_reconnect.py
  WAIT for VPN connection
  NOTIFY user if MFA needed
```

### Step 2: Navigate to Support Portal
```
NAVIGATE https://support.xdr.trendmicro.com/#/admin/products
WAIT for page load
IF login page appears:
  GO TO Step 3 (SSO Login)
ELSE:
  GO TO Step 4 (Search Customer)
```

### Step 3: SSO Login
```
CLICK button.login-form-button ("Log On with Domain Credentials")
WAIT for redirect to corporate ID page

CLICK AAD SSO button (button with "AAD" text)
WAIT for Microsoft SSO page

IF page shows "Face, fingerprint, PIN or security key" (Windows Hello):
  CLICK #idBtn_Back ("Back" button)
  WAIT for "Verify your identity" page

CLICK [data-value="PhoneAppNotification"] ("Approve a request on my Microsoft Authenticator app")
WAIT for "Approve sign in request" page

EXTRACT MFA number from page (large 2-digit number display)
NOTIFY user: "Approve #{number} on Authenticator"

WAIT for page redirect (poll every 2s, timeout 120s)
VERIFY URL contains support.xdr.trendmicro.com/#/admin
```

### Step 4: Search Customer
```
LOCATE input[placeholder*="Company"]
CLEAR existing text
TYPE {customerName}
CLICK .ant-input-search-icon (search button)
WAIT for .ant-table-body results (timeout 5s)
VERIFY customer appears in results table
```

### Step 5: Open Console Modal
```
CLICK .anticon-setting (gear icon in Action column of customer row)
WAIT for .ant-modal with title "Open XDR Console"
```

### Step 6: Fill Console Form
```
# Select case type
CLICK first .ant-select in .ant-modal-body (Case ID type dropdown)
WAIT for .ant-select-dropdown-menu-item options
CLICK option with text "{caseType}" (default: "Salesforce")

# Enter case ID
FOCUS input.ant-input[type="text"] in .ant-modal-body
SET value = "{caseId}" (default: "11111111")
DISPATCH input + change events

# Comments (dynamic reason)
FOCUS textarea in .ant-modal-body
SET value = "{reason}"
DISPATCH input + change events

# Role stays default (Technical Support)
```

### Step 7: Submit & Capture Console URL
```
# Install popup hook BEFORE clicking submit
window.__capturedPopupUrls = []
OVERRIDE window.open to capture URLs

CLICK .ant-modal-footer .ant-btn-primary ("Open Console")
WAIT 3s for popup

# The portal opens a popup to:
# https://signin.v1.trendmicro.com/impersonateproxy/support?token=<JWT>
# Token expires in ~60 seconds!

EXTRACT URL from window.__capturedPopupUrls[0]
```

### Step 8: Navigate to Customer Console
```
# Open captured impersonation URL in new tab (or navigate current)
NAVIGATE {capturedUrl}
WAIT for V1 console to load (redirect chain: signin → portal.xdr.trendmicro.com)
VERIFY V1 console loaded for correct customer

# Now in customer's V1 console as impersonated support user
```

---

## Key Selectors
```
# Login page
button.login-form-button               → "Log On with Domain Credentials"

# Microsoft SSO
#idBtn_Back                            → "Back" (skip Windows Hello)
[data-value="PhoneAppNotification"]    → Authenticator push option

# Support Portal
input[placeholder*="Company"]          → Customer search input
.ant-input-search-icon                 → Search button
.anticon-setting                       → Gear icon (Action column)

# Open Console Modal
.ant-modal-body .ant-select            → Case type / Role dropdowns
.ant-modal-body input.ant-input        → Case ID input
.ant-modal-body textarea               → Comments textarea
.ant-modal-footer .ant-btn-primary     → "Open Console" submit
.ant-modal-footer .ant-btn-default     → "Close" / "Cancel"
```

## Critical Notes
- **Impersonation token expires in ~60 seconds** — must navigate to URL immediately after capture
- **Popup may be blocked** — use window.open hook to capture URL, then navigate manually
- **Windows Hello cannot be automated from WSL** — always click Back → Authenticator
- **VPN required** — support.xdr.trendmicro.com resolves to internal 10.133.x.x
- **Case ID "11111111" is a placeholder** — acceptable per Joel's instruction
- **Reason must be accurate and brief (2-5 words)** — dynamically generated per task
- **Token fires twice** — window.open called twice, only need first URL
