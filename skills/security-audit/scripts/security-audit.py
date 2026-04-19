#!/usr/bin/env python3
"""
Security audit suite for OpenClaw hosts.
Runs 4 audits, posts findings to Slack (or stdout).
Only posts when something needs attention (silent on clean runs unless --force).

Audits:
  1. Credential expiry — known expiry dates, token presence
  2. Exposed ports — unexpected listeners beyond known services
  3. File permissions — sensitive files not world-readable
  4. Plugin integrity — hash deployed extensions, detect changes

Usage:
  python3 security-audit.py              # run all audits
  python3 security-audit.py --audit creds
  python3 security-audit.py --audit ports
  python3 security-audit.py --audit perms
  python3 security-audit.py --audit plugins
  python3 security-audit.py --force      # post even if clean

Config: ~/.openclaw/security-audit.json (optional)
Env: SLACK_BOT_TOKEN, SECURITY_AUDIT_CHANNEL, SECURITY_AUDIT_CONFIG
"""

import json
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Config ---

def load_config() -> dict:
    """Load config from file or env, with defaults."""
    config_path = os.environ.get(
        "SECURITY_AUDIT_CONFIG",
        str(Path.home() / ".openclaw/security-audit.json")
    )
    config = {}
    if Path(config_path).exists():
        try:
            config = json.loads(Path(config_path).read_text())
        except Exception:
            pass

    return {
        "channel": os.environ.get("SECURITY_AUDIT_CHANNEL", config.get("channel", "")),
        "slack_token": os.environ.get("SLACK_BOT_TOKEN", ""),
        "expected_ports": {int(k): v for k, v in config.get("expected_ports", {
            "18789": "openclaw-gateway",
        }).items()},
        "tailscale_ranges": config.get("tailscale_ranges", ["100.", "fd7a:115c:a1e0"]),
        "sensitive_paths": [
            Path(p).expanduser() for p in config.get("sensitive_paths", [
                "~/.openclaw/openclaw.json",
                "~/.openclaw/gateway.json",
                "~/.openclaw/.env",
            ])
        ],
        "credential_expiry": config.get("credential_expiry", {}),
        "warn_days": config.get("warn_days", 60),
        "critical_days": config.get("critical_days", 30),
        "extensions_dir": Path(config.get("extensions_dir", str(Path.home() / ".openclaw/extensions"))),
        "audit_log": Path(config.get("audit_log", str(Path.home() / ".openclaw/workspace/memory/audit-log.md"))),
        "hash_state": Path(config.get("hash_state", str(Path.home() / ".openclaw/workspace/memory/security-hashes.json"))),
    }


CFG = load_config()


# --- Helpers ---

def slack_post(text: str):
    """Post to Slack channel, or print if no token/channel."""
    if not CFG["slack_token"] or not CFG["channel"]:
        print(text)
        return
    import urllib.request
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": CFG["channel"], "text": text}).encode(),
        headers={
            "Authorization": f"Bearer {CFG['slack_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Slack post failed: {e}")
        print(text)


def log_audit(entry: str):
    """Append to audit log."""
    CFG["audit_log"].parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(CFG["audit_log"], "a") as f:
        f.write(f"\n## {ts} — Security Audit (cron)\n{entry}\n")


def get_keyring_value(service: str, key: str) -> str:
    """Get value from Python keyring (best-effort)."""
    try:
        import keyring
        return keyring.get_password(service, key) or ""
    except Exception:
        return ""


# --- Audit 1: Credential Expiry ---

def audit_credentials() -> list[str]:
    """Check credential expiry dates and freshness."""
    findings = []

    # Check configured expiry dates
    for name, expiry_str in CFG["credential_expiry"].items():
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
            label = name.replace("_", " ").title()
            if days_left < 0:
                findings.append(f"🔴 *{label}* expired {abs(days_left)} days ago ({expiry_str}). Rotate immediately.")
            elif days_left < CFG["critical_days"]:
                findings.append(f"🔴 *{label}* expires in *{days_left} days* ({expiry_str}). Rotate immediately.")
            elif days_left < CFG["warn_days"]:
                findings.append(f"🟡 *{label}* expires in *{days_left} days* ({expiry_str}). Plan rotation.")
        except (ValueError, TypeError):
            findings.append(f"🟡 Cannot parse expiry date for `{name}`: `{expiry_str}`")

    # Check common keyring credentials exist
    for service, key, label in [
        ("openclaw", "TRELLO_API_KEY", "Trello API key"),
        ("openclaw", "TRELLO_TOKEN", "Trello token"),
    ]:
        val = get_keyring_value(service, key)
        if not val:
            findings.append(f"🟡 {label} missing from keyring (`{service}/{key}`).")

    return findings


# --- Audit 2: Exposed Ports ---

def audit_ports() -> list[str]:
    """Check for unexpected listening ports."""
    findings = []
    try:
        result = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            local_addr = parts[3]
            if ":" not in local_addr:
                continue

            port_str = local_addr.rsplit(":", 1)[-1]
            try:
                port = int(port_str)
            except ValueError:
                continue

            # Skip loopback
            if local_addr.startswith("127.") or local_addr.startswith("[::1]"):
                continue

            # Skip expected ports
            if port in CFG["expected_ports"]:
                continue

            # Skip Tailscale ranges
            addr_part = local_addr.rsplit(":", 1)[0]
            if any(r in addr_part for r in CFG["tailscale_ranges"]):
                continue

            process_info = parts[-1] if len(parts) > 5 else "unknown"
            findings.append(
                f"🟡 Unexpected port *{port}* listening on non-loopback: "
                f"`{local_addr}` ({process_info})"
            )
    except FileNotFoundError:
        # ss not available (macOS etc.)
        try:
            result = subprocess.run(
                ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                capture_output=True, text=True, timeout=10
            )
            findings.append(f"ℹ️ Port scan via lsof — {len(result.stdout.splitlines()) - 1} listeners found. Review manually.")
        except Exception as e:
            findings.append(f"🟡 Port scan unavailable: {e}")
    except Exception as e:
        findings.append(f"🟡 Port scan failed: {e}")

    return findings


# --- Audit 3: File Permissions ---

def audit_permissions() -> list[str]:
    """Check sensitive files aren't world-readable."""
    findings = []

    for path in CFG["sensitive_paths"]:
        if not path.exists():
            continue
        try:
            stat = path.stat()
            mode = oct(stat.st_mode)[-3:]
            other_bits = int(mode[-1])
            try:
                rel = str(path.relative_to(Path.home()))
            except ValueError:
                rel = str(path)
            if other_bits & 4:
                findings.append(f"🔴 `{rel}` is world-readable (mode {mode}). Fix: `chmod o-r {path}`")
            if other_bits & 2:
                findings.append(f"🔴 `{rel}` is world-writable (mode {mode}). Fix: `chmod o-w {path}`")
        except Exception as e:
            findings.append(f"🟡 Cannot check `{path}`: {e}")

    # Check extensions directory
    if CFG["extensions_dir"].exists():
        for ext_dir in CFG["extensions_dir"].iterdir():
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

    if not CFG["extensions_dir"].exists():
        return [f"ℹ️ No extensions directory at `{CFG['extensions_dir']}`."]

    for ext_dir in sorted(CFG["extensions_dir"].iterdir()):
        if not ext_dir.is_dir():
            continue
        for f in sorted(ext_dir.rglob("*")):
            if f.is_file() and f.suffix in (".ts", ".js", ".json"):
                try:
                    h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                    rel = str(f.relative_to(CFG["extensions_dir"]))
                    current_hashes[rel] = h
                except Exception:
                    pass

    # Load previous hashes
    prev_hashes = {}
    if CFG["hash_state"].exists():
        try:
            prev_hashes = json.loads(CFG["hash_state"].read_text())
        except Exception:
            pass

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
    CFG["hash_state"].parent.mkdir(parents=True, exist_ok=True)
    CFG["hash_state"].write_text(json.dumps(current_hashes, indent=2))

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
        msg = f"🔒 Security audit ({ts}):\n\n" + "\n\n".join(all_findings)
        slack_post(msg)
        log_audit("- *Findings:*\n" + "\n".join(all_findings))
        print(f"[{ts}] {len(all_findings)} finding(s) posted")
    elif force:
        msg = f"🔒 Security audit ({ts}) — all clear. Checked: {', '.join(audit_names)}."
        slack_post(msg)
        log_audit(f"- Audits: {', '.join(audit_names)} — all clean.")
        print(f"[{ts}] Clean (forced post)")
    else:
        log_audit(f"- Audits: {', '.join(audit_names)} — all clean.")
        print(f"[{ts}] Clean (silent)")


if __name__ == "__main__":
    main()
