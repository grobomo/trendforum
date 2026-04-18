#!/usr/bin/env python3
"""Email Sample Extractor for Exchange Online via MS Graph API.

Searches for and downloads email samples (including headers and raw MIME)
from a Microsoft 365 tenant. Designed for security teams that need to collect
missed malicious emails (e.g., subscription bomb attacks) for analysis.

Adaptable to any 365 tenant — configure via config.json or CLI args.

Usage:
    # Interactive: uses config.json for defaults
    python3 extract_samples.py

    # Search by subject pattern
    python3 extract_samples.py --subject "subscription" --days 7

    # Search by sender
    python3 extract_samples.py --sender "noreply@example.com" --days 30

    # Search specific mailbox (requires admin consent / app permissions)
    python3 extract_samples.py --mailbox user@company.com --subject "confirm"

    # Save to specific folder
    python3 extract_samples.py --output ./samples/live-nation-2026-04

    # Dry run — show matches without downloading
    python3 extract_samples.py --dry-run --subject "subscription"

    # Export as EML files (raw MIME)
    python3 extract_samples.py --format eml --subject "subscription"

Requirements:
    - Azure AD / Entra ID app registration with:
      - Mail.Read (delegated) for own mailbox, OR
      - Mail.Read (application) for any mailbox (admin consent required)
    - Credentials stored in system keyring or environment variables
    - MS Graph API access

Config file (config.json):
    {
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id",
        "default_mailbox": "user@company.com",
        "default_output": "./samples",
        "max_results": 50
    }

For Live Nation use case:
    - Configure with Live Nation's tenant creds (they provide app registration)
    - Search for subscription bomb patterns
    - Export raw EML for submission to Trend Micro for analysis
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from email import policy as email_policy
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [email-extractor] %(message)s",
)
log = logging.getLogger(__name__)

# Try to use our existing Graph API library
MSGRAPH_LIB = os.path.expanduser("~/lib/teams-agent")
if MSGRAPH_LIB not in sys.path:
    sys.path.insert(0, MSGRAPH_LIB)

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"


def load_config() -> dict:
    """Load config from config.json if it exists."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_graph_client(config: dict):
    """Initialize Graph API client.

    Supports two modes:
    1. Local tenant (our Entra app) — uses existing TokenManager
    2. External tenant — uses client_credentials flow with config values
    """
    tenant_id = config.get("tenant_id")
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    if tenant_id and client_id and client_secret:
        # External tenant mode — client credentials flow
        return _get_external_client(tenant_id, client_id, client_secret)
    else:
        # Local tenant mode — use our existing auth
        try:
            from lib.msgraph.auth import TokenManager
            from lib.msgraph.client import GraphClient

            tm = TokenManager()
            token = tm.get_token()
            if not token:
                log.error("No valid Graph token from local auth")
                sys.exit(1)
            return GraphClient(token=token), "delegated"
        except Exception as e:
            log.error("Local auth failed: %s", e)
            log.info("To use external tenant, provide tenant_id, client_id, "
                     "client_secret in config.json")
            sys.exit(1)


def _get_external_client(tenant_id: str, client_id: str, client_secret: str):
    """Get Graph client for external tenant using client credentials."""
    import urllib.request
    import urllib.parse

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode()

    req = urllib.request.Request(token_url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            token = result["access_token"]
    except Exception as e:
        log.error("External tenant auth failed: %s", e)
        sys.exit(1)

    # Return a simple client wrapper
    class SimpleGraphClient:
        def __init__(self, token):
            self.token = token
            self.base = "https://graph.microsoft.com/v1.0"

        def get(self, path, params=None):
            url = self.base + path
            if params:
                qs = urllib.parse.urlencode(params)
                url += "?" + qs
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())

        def get_raw(self, path):
            """Get raw bytes (for MIME content)."""
            url = self.base + path
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self.token}",
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()

    return SimpleGraphClient(token), "application"


def build_search_filter(args, config: dict) -> str:
    """Build OData filter string from search criteria."""
    filters = []

    # Date range
    days = args.days or config.get("default_days", 7)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    filters.append(f"receivedDateTime ge {since}")

    # Subject filter
    if args.subject:
        # Use contains for subject search
        filters.append(f"contains(subject, '{args.subject}')")

    # Sender filter
    if args.sender:
        filters.append(
            f"from/emailAddress/address eq '{args.sender}'"
        )

    return " and ".join(filters) if filters else ""


def build_search_query(args) -> str | None:
    """Build KQL search query for $search parameter (broader than $filter)."""
    parts = []
    if args.subject:
        parts.append(f'subject:"{args.subject}"')
    if args.sender:
        parts.append(f'from:"{args.sender}"')
    if args.body_contains:
        parts.append(f'body:"{args.body_contains}"')
    return " AND ".join(parts) if parts else None


def sanitize_filename(s: str, max_len: int = 80) -> str:
    """Make a string safe for use as a filename."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', s)
    s = s.strip('. ')
    return s[:max_len] if s else "no_subject"


def save_email_json(email: dict, output_dir: Path, index: int):
    """Save email metadata as JSON."""
    sender = email.get("from", {}).get("emailAddress", {})
    subject = email.get("subject", "no_subject")
    received = email.get("receivedDateTime", "")

    safe_subject = sanitize_filename(subject)
    filename = f"{index:03d}_{safe_subject}.json"
    filepath = output_dir / filename

    # Build clean metadata
    meta = {
        "id": email.get("id"),
        "internetMessageId": email.get("internetMessageId"),
        "subject": subject,
        "from": f"{sender.get('name', '')} <{sender.get('address', '')}>",
        "toRecipients": [
            f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>"
            for r in email.get("toRecipients", [])
        ],
        "ccRecipients": [
            f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>"
            for r in email.get("ccRecipients", [])
        ],
        "receivedDateTime": received,
        "importance": email.get("importance", "normal"),
        "hasAttachments": email.get("hasAttachments", False),
        "internetMessageHeaders": email.get("internetMessageHeaders", []),
        "bodyPreview": email.get("bodyPreview", ""),
    }

    # Include full body
    body = email.get("body", {})
    meta["body"] = {
        "contentType": body.get("contentType", "text"),
        "content": body.get("content", ""),
    }

    with open(filepath, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return filepath


def save_email_eml(client, email_id: str, output_dir: Path,
                   subject: str, index: int, mailbox: str | None):
    """Save email as raw EML (MIME) file."""
    safe_subject = sanitize_filename(subject)
    filename = f"{index:03d}_{safe_subject}.eml"
    filepath = output_dir / filename

    # Get raw MIME content
    if mailbox:
        path = f"/users/{mailbox}/messages/{email_id}/$value"
    else:
        path = f"/me/messages/{email_id}/$value"

    try:
        raw = client.get_raw(path)
        with open(filepath, "wb") as f:
            f.write(raw)
        return filepath
    except Exception as e:
        log.warning("Failed to get EML for %s: %s", subject[:40], e)
        return None


def search_emails(client, args, config: dict, auth_mode: str) -> list:
    """Search for emails matching criteria."""
    mailbox = args.mailbox or config.get("default_mailbox")
    max_results = args.max_results or config.get("max_results", 50)

    # Build base path
    if mailbox and auth_mode == "application":
        base_path = f"/users/{mailbox}/messages"
    else:
        base_path = "/me/messages"
        if mailbox:
            log.warning("--mailbox requires application permissions; "
                        "using /me/messages instead")

    params = {
        "$top": str(min(max_results, 100)),
        "$orderby": "receivedDateTime desc",
        "$select": ("id,subject,from,toRecipients,ccRecipients,"
                    "receivedDateTime,bodyPreview,body,importance,"
                    "hasAttachments,internetMessageId,internetMessageHeaders,"
                    "flag"),
    }

    # Prefer $search for flexibility, fall back to $filter
    search_query = build_search_query(args)
    if search_query:
        params["$search"] = f'"{search_query}"'
        # $search and $filter can't always be combined
        # Add date filter separately if no $search
    else:
        filter_str = build_search_filter(args, config)
        if filter_str:
            params["$filter"] = filter_str

    log.info("Searching %s (max %d results)...", base_path, max_results)

    all_emails = []
    try:
        result = client.get(base_path, params=params)
        emails = result.get("value", [])
        all_emails.extend(emails)

        # Handle pagination
        next_link = result.get("@odata.nextLink")
        while next_link and len(all_emails) < max_results:
            # Strip base URL for our client
            next_path = next_link.replace("https://graph.microsoft.com/v1.0", "")
            result = client.get(next_path)
            all_emails.extend(result.get("value", []))
            next_link = result.get("@odata.nextLink")
            time.sleep(0.5)  # Rate limit courtesy

    except Exception as e:
        log.error("Search failed: %s", e)
        return []

    return all_emails[:max_results]


def main():
    parser = argparse.ArgumentParser(
        description="Extract email samples from Exchange Online via MS Graph API"
    )
    parser.add_argument("--subject", help="Search by subject (contains)")
    parser.add_argument("--sender", help="Search by sender email address")
    parser.add_argument("--body-contains", help="Search by body content")
    parser.add_argument("--mailbox", help="Target mailbox (requires app permissions)")
    parser.add_argument("--days", type=int, help="Look back N days (default: 7)")
    parser.add_argument("--max-results", type=int, help="Max emails to retrieve (default: 50)")
    parser.add_argument("--output", "-o", help="Output directory (default: ./samples)")
    parser.add_argument("--format", choices=["json", "eml", "both"],
                        default="both",
                        help="Output format: json (metadata), eml (raw MIME), both")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show matches without downloading")
    parser.add_argument("--include-headers", action="store_true",
                        help="Request internet message headers (slower)")
    parser.add_argument("--config", help="Path to config.json")

    args = parser.parse_args()

    # Load config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = CONFIG_FILE
    try:
        with open(config_path) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}

    if not (args.subject or args.sender or args.body_contains):
        log.error("Specify at least one search criterion: --subject, --sender, or --body-contains")
        parser.print_help()
        sys.exit(1)

    # Output directory
    output_dir = Path(args.output or config.get("default_output", "./samples"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_dir / timestamp

    # Get client
    client, auth_mode = get_graph_client(config)
    log.info("Authenticated (%s mode)", auth_mode)

    # Search
    emails = search_emails(client, args, config, auth_mode)

    if not emails:
        log.info("No emails found matching criteria")
        return

    log.info("Found %d email(s)", len(emails))

    if args.dry_run:
        print(f"\n{'='*70}")
        print(f"DRY RUN — {len(emails)} match(es)")
        print(f"{'='*70}\n")
        for i, email in enumerate(emails, 1):
            sender = email.get("from", {}).get("emailAddress", {})
            print(f"{i:3d}. [{email.get('receivedDateTime', '')[:16]}] "
                  f"From: {sender.get('name', '')} <{sender.get('address', '')}>"
                  f"\n     Subject: {email.get('subject', '(none)')}"
                  f"\n     Preview: {email.get('bodyPreview', '')[:100]}")
            print()
        return

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Saving to %s", output_dir)

    mailbox = args.mailbox or config.get("default_mailbox")
    saved = {"json": 0, "eml": 0}

    for i, email in enumerate(emails, 1):
        subject = email.get("subject", "no_subject")
        sender = email.get("from", {}).get("emailAddress", {}).get("address", "")
        log.info("  [%d/%d] %s — %s", i, len(emails), sender, subject[:60])

        if args.format in ("json", "both"):
            fp = save_email_json(email, output_dir, i)
            if fp:
                saved["json"] += 1

        if args.format in ("eml", "both"):
            eid = email.get("id")
            fp = save_email_eml(client, eid, output_dir, subject, i, mailbox)
            if fp:
                saved["eml"] += 1

        time.sleep(0.3)  # Rate limit courtesy

    # Summary
    print(f"\n{'='*70}")
    print(f"COMPLETE — {len(emails)} email(s) processed")
    print(f"  JSON files: {saved['json']}")
    print(f"  EML files:  {saved['eml']}")
    print(f"  Output dir: {output_dir}")
    print(f"{'='*70}")

    # Write manifest
    manifest = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "search_criteria": {
            "subject": args.subject,
            "sender": args.sender,
            "body_contains": args.body_contains,
            "days": args.days or config.get("default_days", 7),
            "mailbox": mailbox,
        },
        "results": len(emails),
        "auth_mode": auth_mode,
        "files": {
            "json": saved["json"],
            "eml": saved["eml"],
        },
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("Manifest written to %s", manifest_path)


if __name__ == "__main__":
    main()
