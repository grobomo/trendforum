#!/usr/bin/env python3
"""
Exchange Online Email Sample Puller
====================================
Pull email samples from Exchange Online via Microsoft Graph API.
Designed for security teams to collect missed/suspicious emails for analysis.

Requirements:
- Azure AD app registration with Mail.Read application permission
- Tenant ID, Client ID, Client Secret

Usage:
    python3 pull_emails.py --config config.json --query "subject:invoice" --output ./samples
    python3 pull_emails.py --config config.json --sender "suspicious@example.com" --output ./samples
    python3 pull_emails.py --config config.json --recipient "user@company.com" --days 7 --output ./samples

Output: Creates a folder with individual .eml files + summary.json

Adaptable: Update config.json with different tenant credentials to use with any 365 tenant.
"""

import argparse
import json
import os
import sys
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' module required. Install with: pip install requests")
    sys.exit(1)


def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get OAuth2 access token using client credentials flow."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_emails(token: str, user_email: str, query: str = None, sender: str = None,
                  recipient: str = None, subject: str = None, days: int = 30,
                  limit: int = 50) -> list:
    """Search for emails matching criteria."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Build OData filter
    filters = []
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    filters.append(f"receivedDateTime ge {since}")
    
    if sender:
        filters.append(f"from/emailAddress/address eq '{sender}'")
    
    filter_str = " and ".join(filters)
    
    # Build URL
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
    params = {
        "$filter": filter_str,
        "$top": min(limit, 50),
        "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments,internetMessageId",
        "$orderby": "receivedDateTime desc"
    }
    
    if query:
        params["$search"] = f'"{query}"'
        # Can't use $filter with $search on some fields, adjust
        params.pop("$filter", None)
    
    if subject:
        params["$search"] = f'"subject:{subject}"'
        params.pop("$filter", None)
    
    all_messages = []
    while url and len(all_messages) < limit:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 403:
            print(f"ERROR: Access denied for user {user_email}. Ensure Mail.Read permission is granted.")
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()
        messages = data.get("value", [])
        all_messages.extend(messages)
        url = data.get("@odata.nextLink")
        params = {}  # nextLink includes params
    
    return all_messages[:limit]


def download_email_mime(token: str, user_email: str, message_id: str) -> bytes:
    """Download full email in MIME format (.eml)."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/$value"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.content


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Create safe filename from email subject."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    return safe.strip()[:max_len] or "untitled"


def main():
    parser = argparse.ArgumentParser(
        description="Pull email samples from Exchange Online via Graph API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pull emails from a specific sender in the last 7 days
  python3 pull_emails.py --config config.json --user victim@company.com --sender attacker@evil.com --days 7

  # Search by subject keyword
  python3 pull_emails.py --config config.json --user user@company.com --query "subscription confirmation" --days 30

  # Pull all emails to a specific recipient (subscription bomb detection)
  python3 pull_emails.py --config config.json --user target@company.com --days 3 --limit 100

Config file format (config.json):
  {
    "tenant_id": "your-tenant-id",
    "client_id": "your-app-client-id",
    "client_secret": "your-app-client-secret"
  }
        """
    )
    parser.add_argument("--config", required=True, help="Path to config.json with Azure AD credentials")
    parser.add_argument("--user", required=True, help="Target user's email address (mailbox to search)")
    parser.add_argument("--sender", help="Filter by sender email address")
    parser.add_argument("--recipient", help="Filter by recipient email address")
    parser.add_argument("--subject", help="Search by subject keyword")
    parser.add_argument("--query", help="Free-text search query")
    parser.add_argument("--days", type=int, default=30, help="Search window in days (default: 30)")
    parser.add_argument("--limit", type=int, default=50, help="Max emails to pull (default: 50)")
    parser.add_argument("--output", default="./email_samples", help="Output directory (default: ./email_samples)")
    parser.add_argument("--no-download", action="store_true", help="List matching emails without downloading")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    # Load config
    try:
        with open(args.config) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {args.config}")
        print("Create one with: {\"tenant_id\": \"...\", \"client_id\": \"...\", \"client_secret\": \"...\"}")
        sys.exit(1)
    
    tenant_id = config["tenant_id"]
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    
    # Authenticate
    print(f"Authenticating with tenant {tenant_id[:8]}...")
    token = get_access_token(tenant_id, client_id, client_secret)
    print("✓ Authenticated")
    
    # Search
    print(f"Searching mailbox: {args.user} (last {args.days} days, limit {args.limit})...")
    messages = search_emails(
        token, args.user,
        query=args.query, sender=args.sender,
        recipient=args.recipient, subject=args.subject,
        days=args.days, limit=args.limit
    )
    
    print(f"Found {len(messages)} matching email(s)")
    
    if not messages:
        return
    
    # Summary
    summary = []
    for i, msg in enumerate(messages, 1):
        info = {
            "index": i,
            "subject": msg.get("subject", "(no subject)"),
            "from": msg.get("from", {}).get("emailAddress", {}).get("address", "?"),
            "to": [r.get("emailAddress", {}).get("address", "?") for r in msg.get("toRecipients", [])],
            "received": msg.get("receivedDateTime", ""),
            "has_attachments": msg.get("hasAttachments", False),
            "preview": msg.get("bodyPreview", "")[:100],
            "message_id": msg.get("internetMessageId", ""),
            "graph_id": msg.get("id", "")
        }
        summary.append(info)
        if not args.json:
            print(f"\n  [{i}] {info['received'][:16]}")
            print(f"      From: {info['from']}")
            print(f"      Subject: {info['subject'][:80]}")
            if info['has_attachments']:
                print(f"      📎 Has attachments")
    
    if args.json:
        print(json.dumps(summary, indent=2))
        return
    
    if args.no_download:
        return
    
    # Download
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownloading {len(messages)} email(s) to {output_dir}/...")
    
    for i, msg in enumerate(messages, 1):
        subject = sanitize_filename(msg.get("subject", "untitled"))
        date_str = msg.get("receivedDateTime", "")[:10]
        filename = f"{date_str}_{subject}.eml"
        filepath = output_dir / filename
        
        # Avoid overwrite
        counter = 1
        while filepath.exists():
            filepath = output_dir / f"{date_str}_{subject}_{counter}.eml"
            counter += 1
        
        try:
            eml_data = download_email_mime(token, args.user, msg["id"])
            filepath.write_bytes(eml_data)
            print(f"  ✓ [{i}/{len(messages)}] {filepath.name} ({len(eml_data)} bytes)")
        except Exception as e:
            print(f"  ✗ [{i}/{len(messages)}] Failed: {e}")
    
    # Write summary
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "pulled_at": datetime.now(timezone.utc).isoformat(),
            "user": args.user,
            "query": args.query,
            "sender": args.sender,
            "days": args.days,
            "count": len(messages),
            "emails": summary
        }, f, indent=2)
    print(f"\n✓ Summary written to {summary_path}")
    print(f"✓ {len(messages)} email sample(s) saved to {output_dir}/")


if __name__ == "__main__":
    main()
