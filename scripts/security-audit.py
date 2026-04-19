#!/usr/bin/env python3
"""
Security audit suite for OpenClaw host.
Runs 4 audits, posts findings to #coco-chat via Slack.
Only posts when something needs attention (no spam on clean runs).

Audits:
  1. Credential expiry — Entra client secret, token freshness
  2. Exposed ports — unexpected listeners beyond gateway
  3. File permissions — sensitive files not world-readable
  4. Plugin integrity — hash deployed extensions, detect changes

Usage:
  python3 security-audit.py              # run all audits
  python3 security-audit.py --audit creds   # run one audit
  python3 security-audit.py --audit ports
  python3 security-audit.py --audit perms
  python3 security-audit.py --audit plugins
  python3 security-audit.py --force      # post even if clean
"""

import json
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Config ---
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
CHANNEL = "C0ATJE19YRY"  # #coco-chat
AUDIT_LOG = Path.home() / ".openclaw/workspace/memory/audit-log.md"
HASH_STATE = Path.home() / ".openclaw/workspace/memory/security-hashes.json"
EXTENSIONS_DIR = Path.home() / ".openclaw/extensions"
OPENCLAW_DIR = Path.home() / ".openclaw"
WORKSPACE_DIR = OPENCLAW_DIR / "workspace"

# Known-good listening ports (port: description)
EXPECTED_PORTS = {
    18789: "openclaw-gateway",
    3000: "openclaw-web",
    8080: "signal-cli",
    443: "tailscale-proxy",
    8443: "tailscale-proxy",
    53: "tailscale-dns",
    631: "cups-printing",
}

# Sensitive files/dirs that should NOT be world-readable
SENSITIVE_PATHS = [
    OPENCLAW_DIR / "openclaw.json",
    OPENCLAW_DIR / "gateway.json",
    OPENCLAW_DIR / ".env",
    WORKSPACE_DIR / "scripts" / "poll_all.py",
    WORKSPACE_DIR / "scripts" / "entra-cred-store.py",
]

# --- Helpers ---

def slack_post(text: str):
    """Post to Slack channel."""
    if not SLACK_TOKEN:
        print(f"[no SLACK_TOKEN] {text}")
        return
    import urllib.request
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": CHANNEL, "text": text}).encode(),
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Slack post failed: {e}")


def log_audit(entry: str):
    """Append to audit log."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(AUDIT_LOG, "a") as f:
        f.write(f"\n## {ts} — Security Audit (cron)\n{entry}\n")


def get_keyring_value(service: str, key: str) -> str:
    """Get value from Python keyring."""
    try:
        import keyring
        return keyring.get_password(service, key) or ""
    except Exception:
        return ""


# --- Audit 1: Credential Expiry ---

def audit_credentials() -> list[str]:
    """Check credential expiry dates and freshness."""
    findings = []

    # Entra client secret — known expiry 2026-07-16
    entra_expiry = datetime(2026, 7, 16, tzinfo=timezone.utc)
    days_left = (entra_expiry - datetime.now(timezone.utc)).days
    if days_left < 30:
        findings.append(f"🔴 Entra client secret expires in *{days_left} days* (2026-07-16). Rotate immediately.")
    elif days_left < 60:
        findings.append(f"🟡 Entra client secret expires in *{days_left} days* (2026-07-16). Plan rotation.")
    # else: fine, don't report

    # Check Trello token exists
    trello_key = get_keyring_value("openclaw", "TRELLO_API_KEY")
    trello_token = get_keyring_value("openclaw", "TRELLO_TOKEN")
    if not trello_key or not trello_token:
        findings.append("🔴 Trello API credentials missing from keyring.")

    # Check V1 API key exists
    v1_key = get_keyring_value("openclaw", "V1_API_KEY")
    if not v1_key:
        findings.append("🟡 V1_API_KEY missing from keyring (may not be needed).")

    # Graph API env vars are set in Teams poller service, not expected in cron context
    # Skip this check — not a meaningful finding from cron

    return findings


# --- Audit 2: Exposed Ports ---

def audit_ports() -> list[str]:
    """Check for unexpected listening ports."""
    findings = []
    try:
        result = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n")[1:]:  # skip header
            parts = line.split()
            if len(parts) < 4:
                continue
            local_addr = parts[3]
            # Extract port
            if ":" in local_addr:
                port_str = local_addr.rsplit(":", 1)[-1]
                try:
                    port = int(port_str)
                except ValueError:
                    continue
                # Skip loopback-only listeners and expected ports
                if local_addr.startswith("127.") or local_addr.startswith("[::1]"):
                    continue
                if port not in EXPECTED_PORTS:
                    # Skip Tailscale ephemeral ports (100.x.x.x and fd7a: ranges)
                    addr_part = local_addr.rsplit(":", 1)[0]
                    if addr_part.startswith("100.") or "fd7a:115c:a1e0" in addr_part:
                        continue
                    process_info = parts[-1] if len(parts) > 5 else "unknown"
                    findings.append(f"🟡 Unexpected port *{port}* listening on non-loopback: `{local_addr}` ({process_info})")
    except Exception as e:
        findings.append(f"🟡 Port scan failed: {e}")

    return findings


# --- Audit 3: File Permissions ---

def audit_permissions() -> list[str]:
    """Check sensitive files aren't world-readable."""
    findings = []
    for path in SENSITIVE_PATHS:
        if not path.exists():
            continue
        try:
            stat = path.stat()
            mode = oct(stat.st_mode)[-3:]
            # Check if world-readable (last digit has read bit)
            if int(mode[-1]) & 4:
                findings.append(f"🔴 `{path.relative_to(Path.home())}` is world-readable (mode {mode}). Fix: `chmod o-r {path}`")
            # Check if world-writable
            if int(mode[-1]) & 2:
                findings.append(f"🔴 `{path.relative_to(Path.home())}` is world-writable (mode {mode}). Fix: `chmod o-w {path}`")
        except Exception as e:
            findings.append(f"🟡 Cannot check `{path}`: {e}")

    # Also check the extensions directory
    if EXTENSIONS_DIR.exists():
        for ext_dir in EXTENSIONS_DIR.iterdir():
            if ext_dir.is_dir():
                for f in ext_dir.glob("*.ts"):
                    try:
                        mode = oct(f.stat().st_mode)[-3:]
                        if int(mode[-1]) & 2:
                            findings.append(f"🔴 Plugin `{f.name}` in `{ext_dir.name}` is world-writable (mode {mode})")
                    except Exception:
                        pass

    return findings


# --- Audit 4: Plugin Integrity ---

def audit_plugins() -> list[str]:
    """Hash deployed plugins, detect changes from known-good state."""
    findings = []
    current_hashes = {}

    if not EXTENSIONS_DIR.exists():
        findings.append("🟡 No extensions directory found.")
        return findings

    for ext_dir in sorted(EXTENSIONS_DIR.iterdir()):
        if not ext_dir.is_dir():
            continue
        for f in sorted(ext_dir.rglob("*")):
            if f.is_file() and f.suffix in (".ts", ".js", ".json"):
                try:
                    h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                    rel = str(f.relative_to(EXTENSIONS_DIR))
                    current_hashes[rel] = h
                except Exception:
                    pass

    # Load previous hashes
    prev_hashes = {}
    if HASH_STATE.exists():
        try:
            prev_hashes = json.loads(HASH_STATE.read_text())
        except Exception:
            pass

    # Compare
    if prev_hashes:
        for path, h in current_hashes.items():
            if path in prev_hashes and prev_hashes[path] != h:
                findings.append(f"🟡 Plugin file changed: `{path}` (was `{prev_hashes[path][:8]}…`, now `{h[:8]}…`)")
        for path in prev_hashes:
            if path not in current_hashes:
                findings.append(f"🟡 Plugin file removed: `{path}`")
        for path in current_hashes:
            if path not in prev_hashes:
                findings.append(f"ℹ️ New plugin file: `{path}`")
    else:
        findings.append(f"ℹ️ First run — baseline recorded for {len(current_hashes)} plugin files.")

    # Save current as new baseline
    HASH_STATE.parent.mkdir(parents=True, exist_ok=True)
    HASH_STATE.write_text(json.dumps(current_hashes, indent=2))

    return findings


# --- Main ---

AUDITS = {
    "creds": ("Credential Expiry", audit_credentials),
    "ports": ("Exposed Ports", audit_ports),
    "perms": ("File Permissions", audit_permissions),
    "plugins": ("Plugin Integrity", audit_plugins),
}


def main():
    force = "--force" in sys.argv
    selected = None
    if "--audit" in sys.argv:
        idx = sys.argv.index("--audit")
        if idx + 1 < len(sys.argv):
            selected = sys.argv[idx + 1]

    all_findings = []
    audit_names = []

    for key, (name, fn) in AUDITS.items():
        if selected and key != selected:
            continue
        audit_names.append(name)
        try:
            results = fn()
            if results:
                all_findings.append(f"*{name}:*\n" + "\n".join(f"  • {r}" for r in results))
        except Exception as e:
            all_findings.append(f"*{name}:* ⚠️ Audit failed: {e}")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if all_findings:
        msg = f"🌴 Security audit ({ts}):\n\n" + "\n\n".join(all_findings) + "\n🌴"
        slack_post(msg)
        log_audit("- *Findings:*\n" + "\n".join(all_findings))
        print(f"[{ts}] {len(all_findings)} finding(s) posted to Slack")
    elif force:
        msg = f"🌴 Security audit ({ts}) — all clear. Checked: {', '.join(audit_names)}. 🌴"
        slack_post(msg)
        log_audit(f"- Audits: {', '.join(audit_names)} — all clean.")
        print(f"[{ts}] Clean (forced post)")
    else:
        log_audit(f"- Audits: {', '.join(audit_names)} — all clean.")
        print(f"[{ts}] Clean (silent)")


if __name__ == "__main__":
    main()
