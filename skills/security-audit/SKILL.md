---
name: security-audit
description: >-
  Automated security audits for OpenClaw hosts — credential expiry, exposed ports, file permissions,
  and plugin integrity. Use when setting up periodic security monitoring, running on-demand audits,
  or when the user asks about host security posture. Runs standalone via cron or on-demand via the
  agent. Posts findings to a configured channel and stays silent when clean. NOT for initial host
  hardening (use healthcheck skill), firewall/SSH config changes, or OS-level security policies.
---

# Security Audit

Automated, periodic security audits for OpenClaw hosts. Designed to run unattended via cron and alert only when something needs attention.

## Audits

Four audit modules, all in one script:

1. **Credential expiry** — monitors known credential expiry dates, checks token presence in keyring
2. **Exposed ports** — scans for unexpected non-loopback listeners, ignores known services
3. **File permissions** — checks sensitive OpenClaw files aren't world-readable/writable
4. **Plugin integrity** — SHA-256 hashes all deployed extension files, detects changes between runs

## Quick Start

Run all audits (silent if clean):

```bash
python3 {baseDir}/scripts/security-audit.py
```

Run with forced output (always reports, even if clean):

```bash
python3 {baseDir}/scripts/security-audit.py --force
```

Run a single audit:

```bash
python3 {baseDir}/scripts/security-audit.py --audit creds
python3 {baseDir}/scripts/security-audit.py --audit ports
python3 {baseDir}/scripts/security-audit.py --audit perms
python3 {baseDir}/scripts/security-audit.py --audit plugins
```

## Configuration

The script uses environment variables and a config file for customization:

### Environment Variables

- `SLACK_BOT_TOKEN` — Slack bot token for posting findings (optional; prints to stdout if unset)
- `SECURITY_AUDIT_CHANNEL` — Slack channel ID for alerts (default: none, must be set for Slack delivery)
- `SECURITY_AUDIT_CONFIG` — path to config JSON (optional)

### Config File (`~/.openclaw/security-audit.json`)

```json
{
  "channel": "C0XXXXXXXX",
  "expected_ports": {
    "18789": "openclaw-gateway",
    "3000": "openclaw-web"
  },
  "tailscale_ranges": ["100.", "fd7a:115c:a1e0"],
  "sensitive_paths": [
    "~/.openclaw/openclaw.json",
    "~/.openclaw/.env"
  ],
  "credential_expiry": {
    "entra_client_secret": "2026-07-16"
  },
  "warn_days": 60,
  "critical_days": 30
}
```

All fields are optional — the script has sensible defaults.

## Cron Setup

Recommended schedule:

```bash
# Daily — silent unless findings
0 6 * * * python3 /path/to/security-audit.py >> /tmp/security-audit.log 2>&1

# Weekly full report (Sundays)
0 12 * * 0 python3 /path/to/security-audit.py --force >> /tmp/security-audit.log 2>&1
```

## Output

- Findings post to configured Slack channel with severity indicators (🔴 critical, 🟡 warning, ℹ️ info)
- All runs (clean or not) append to `~/.openclaw/workspace/memory/audit-log.md`
- Plugin hashes stored in `~/.openclaw/workspace/memory/security-hashes.json`
- Silent on clean runs unless `--force` is passed

## Extending

Add new audit modules by defining a function that returns a `list[str]` of findings and registering it in the `AUDITS` dict. Each finding should include a severity emoji and actionable fix.

## Relationship to Healthcheck Skill

This skill handles *ongoing monitoring* — automated, periodic, lightweight checks. The `healthcheck` skill handles *initial hardening* — interactive, one-time host security configuration (firewalls, SSH, OS updates). Use both together: healthcheck for setup, security-audit for ongoing vigilance.
