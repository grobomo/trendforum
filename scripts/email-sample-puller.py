#!/usr/bin/env python3
"""Pull email samples from Exchange Online via Microsoft Graph API.

Designed for security teams to collect missed subscription bomb / phishing
email samples. Adaptable to any 365 tenant with proper Graph API permissions.

Usage:
    python3 email-sample-puller.py --query "subscription bomb" --folder inbox --days 7 --output ./samples
    python3 email-sample-puller.py --sender "noreply@evil.com" --days 30 --output ./samples
    python3 email-sample-puller.py --subject "confirm your subscription" --days 14 --output ./samples --eml

Requirements:
    - Microsoft Graph API token with Mail.Read or Mail.ReadWrite scope
    - Token manager from teams-agent lib OR standalone MSAL auth

Outputs per email:
    - .json metadata (subject, sender, recipients, dates, headers)
    - .html body
    - .txt body (plain text)
    - .eml full MIME (optional, if --eml flag)
    - attachments saved to subfolder
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Try importing from teams-agent lib, fall back to standalone
try:
    sys.path.insert(0, str(Path.home() / "lib" / "teams-agent"))
    from lib.msgraph.auth import TokenManager
    def get_token():
        return TokenManager().get_token()
except ImportError:
    def get_token():
        """Standalone: read token from env or file."""
        token = os.environ.get("GRAPH_TOKEN")
        if not token:
            token_file = Path.home() / ".openclaw" / "graph-token.txt"
            if token_file.exists():
                token = token_file.read_text().strip()
        if not token:
            print("ERROR: No Graph API token. Set GRAPH_TOKEN env var or place in ~/.openclaw/graph-token.txt", file=sys.stderr)
            sys.exit(1)
        return token

import requests


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def search_emails(token: str, query: str = None, sender: str = None,
                  subject: str = None, folder: str = None, days: int = 7,
                  limit: int = 50) -> list:
    """Search for emails matching criteria."""
    headers = {"Authorization": f"Bearer {token}"}

    # Build filter/search
    params = {
        "$top": min(limit, 50),
        "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,hasAttachments,internetMessageHeaders,body,bodyPreview",
    }

    # Date filter
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    search_parts = []
    if query:
        search_parts.append(query)
    if sender:
        search_parts.append(f"from:{sender}")
    if subject:
        search_parts.append(f"subject:{subject}")

    if search_parts:
        params["$search"] = f'"{" ".join(search_parts)}"'

    # Build URL
    if folder:
        url = f"{GRAPH_BASE}/me/mailFolders/{folder}/messages"
    else:
        url = f"{GRAPH_BASE}/me/messages"

    all_messages = []
    while url and len(all_messages) < limit:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"API error {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            break

        data = resp.json()
        messages = data.get("value", [])

        # Filter by date manually (search doesn't always respect date filters)
        for msg in messages:
            received = msg.get("receivedDateTime", "")
            if received >= since:
                all_messages.append(msg)

        url = data.get("@odata.nextLink")
        params = {}  # nextLink includes params

    return all_messages[:limit]


def download_attachments(token: str, message_id: str, output_dir: Path) -> list:
    """Download all attachments for a message."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return []

    attachments = resp.json().get("value", [])
    saved = []

    for att in attachments:
        if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
            filename = att.get("name", "attachment")
            # Sanitize filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = output_dir / filename

            import base64
            content = base64.b64decode(att.get("contentBytes", ""))
            filepath.write_bytes(content)
            saved.append(str(filepath))

    return saved


def get_mime_content(token: str, message_id: str) -> bytes:
    """Get full MIME content of a message (.eml format)."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/me/messages/{message_id}/$value"

    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.content
    return b""


def save_email(token: str, msg: dict, output_dir: Path, save_eml: bool = False) -> dict:
    """Save a single email to disk."""
    msg_id = msg["id"]
    received = msg.get("receivedDateTime", "unknown")[:19].replace(":", "-")
    sender = msg.get("from", {}).get("emailAddress", {}).get("address", "unknown")
    subject_clean = re.sub(r'[<>:"/\\|?*]', '_', msg.get("subject", "no-subject"))[:60]

    # Create per-email directory
    dirname = f"{received}_{sender}_{subject_clean}"
    email_dir = output_dir / dirname
    email_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    metadata = {
        "id": msg_id,
        "subject": msg.get("subject"),
        "from": msg.get("from", {}).get("emailAddress"),
        "to": [r["emailAddress"] for r in msg.get("toRecipients", [])],
        "cc": [r["emailAddress"] for r in msg.get("ccRecipients", [])],
        "receivedDateTime": msg.get("receivedDateTime"),
        "hasAttachments": msg.get("hasAttachments"),
        "headers": {
            h["name"]: h["value"]
            for h in (msg.get("internetMessageHeaders") or [])
            if h["name"].lower() in [
                "x-mailer", "x-originating-ip", "authentication-results",
                "dkim-signature", "received-spf", "arc-authentication-results",
                "x-ms-exchange-organization-scl", "x-forefront-antispam-report",
                "return-path", "message-id"
            ]
        }
    }
    (email_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # Save body
    body = msg.get("body", {})
    if body.get("contentType") == "html":
        (email_dir / "body.html").write_text(body.get("content", ""))
        # Also save plain text version
        text = re.sub(r'<[^>]+>', ' ', body.get("content", ""))
        text = re.sub(r'\s+', ' ', text).strip()
        (email_dir / "body.txt").write_text(text)
    else:
        (email_dir / "body.txt").write_text(body.get("content", ""))

    # Save attachments
    att_dir = email_dir / "attachments"
    att_dir.mkdir(exist_ok=True)
    attachments = download_attachments(token, msg_id, att_dir)

    # Save EML if requested
    if save_eml:
        eml_content = get_mime_content(token, msg_id)
        if eml_content:
            (email_dir / "message.eml").write_bytes(eml_content)

    return {
        "dir": str(email_dir),
        "subject": msg.get("subject"),
        "from": sender,
        "received": msg.get("receivedDateTime"),
        "attachments": len(attachments),
        "eml_saved": save_eml and (email_dir / "message.eml").exists()
    }


def main():
    parser = argparse.ArgumentParser(description="Pull email samples from Exchange Online")
    parser.add_argument("--query", help="Search query (freetext)")
    parser.add_argument("--sender", help="Filter by sender address")
    parser.add_argument("--subject", help="Filter by subject line")
    parser.add_argument("--folder", help="Mail folder (inbox, junkemail, etc.)")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--limit", type=int, default=50, help="Max emails to pull (default: 50)")
    parser.add_argument("--output", default="./email-samples", help="Output directory")
    parser.add_argument("--eml", action="store_true", help="Also save full .eml MIME content")
    parser.add_argument("--dry-run", action="store_true", help="List matches without downloading")

    args = parser.parse_args()

    if not any([args.query, args.sender, args.subject]):
        print("ERROR: Specify at least one of --query, --sender, or --subject", file=sys.stderr)
        sys.exit(1)

    token = get_token()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching emails (last {args.days} days, limit {args.limit})...")
    messages = search_emails(
        token, query=args.query, sender=args.sender, subject=args.subject,
        folder=args.folder, days=args.days, limit=args.limit
    )

    print(f"Found {len(messages)} matching emails")

    if args.dry_run:
        for msg in messages:
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "?")
            print(f"  [{msg['receivedDateTime'][:16]}] {sender}: {msg['subject'][:60]}")
        return

    results = []
    for i, msg in enumerate(messages, 1):
        print(f"  [{i}/{len(messages)}] Saving: {msg['subject'][:50]}...")
        result = save_email(token, msg, output_dir, save_eml=args.eml)
        results.append(result)

    # Save manifest
    manifest = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "sender": args.sender,
        "subject": args.subject,
        "days": args.days,
        "total": len(results),
        "emails": results
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\nDone! {len(results)} emails saved to {output_dir}")
    print(f"Manifest: {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
