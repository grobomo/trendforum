# Exchange Online Email Sample Puller — User Guide

## What This Does
Pulls email samples from Exchange Online mailboxes via Microsoft Graph API. Designed for security teams who need to collect missed/suspicious emails for Trend Micro analysis without interrupting end users.

## Prerequisites

### 1. Azure AD App Registration
1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Click **New registration**
3. Name it something like "Email Sample Puller"
4. Under **API permissions**, add:
   - Microsoft Graph → Application → **Mail.Read** (application-level, not delegated)
5. Grant admin consent
6. Under **Certificates & secrets**, create a new client secret
7. Note down: **Tenant ID**, **Application (client) ID**, and **Client Secret**

### 2. Create Config File
Create `config.json`:
```json
{
  "tenant_id": "your-tenant-id-here",
  "client_id": "your-app-client-id-here",
  "client_secret": "your-client-secret-here"
}
```

### 3. Install Python (if needed)
- Python 3.8+ required
- Install requests: `pip install requests`

## Usage Examples

### Pull emails from a specific sender (subscription bomb investigation)
```bash
python3 pull_emails.py \
  --config config.json \
  --user victim@company.com \
  --sender "newsletter@spam-domain.com" \
  --days 7 \
  --output ./samples
```

### Search by subject keyword
```bash
python3 pull_emails.py \
  --config config.json \
  --user user@company.com \
  --query "subscription confirmation" \
  --days 30
```

### Pull all recent emails to a targeted user (subscription bomb)
```bash
python3 pull_emails.py \
  --config config.json \
  --user target@company.com \
  --days 3 \
  --limit 200 \
  --output ./bomb-samples
```

### List emails without downloading (preview mode)
```bash
python3 pull_emails.py \
  --config config.json \
  --user user@company.com \
  --sender "attacker@evil.com" \
  --no-download
```

### JSON output (for automation)
```bash
python3 pull_emails.py \
  --config config.json \
  --user user@company.com \
  --days 7 \
  --json > results.json
```

## Output
- Individual `.eml` files (full MIME format — can be opened in Outlook or uploaded to Trend support cases)
- `summary.json` with metadata for all pulled emails

## Adapting for Another Tenant
Just create a new `config.json` with the other tenant's credentials. The script works with any Microsoft 365 tenant where you have the app registration set up.

## Security Notes
- The app registration has **read-only** access to mailboxes — it cannot send, delete, or modify emails
- Store `config.json` securely — it contains credentials that can read any mailbox in the tenant
- Consider using Azure Key Vault for production deployments
- Audit logs in Azure AD will show all Graph API access

## Troubleshooting
- **403 Forbidden**: App doesn't have Mail.Read permission, or admin consent wasn't granted
- **401 Unauthorized**: Credentials expired or incorrect
- **No results**: Try broadening the search (increase `--days`, remove filters)
- **Timeout**: Large mailboxes may be slow; reduce `--limit`

## For ChatGPT Enterprise Users
Copy this guide and the script to your ChatGPT workspace. Ask ChatGPT to:
1. Help you set up the Azure AD app registration
2. Run the script with your specific parameters
3. Analyze the downloaded `.eml` files for indicators of compromise
