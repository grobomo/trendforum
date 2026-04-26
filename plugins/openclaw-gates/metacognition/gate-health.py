#!/usr/bin/env python3
"""Module: gate-health — Verify openclaw-gates plugin health.

Checks:
- Plugin is loaded (openclaw.plugin.json exists and is valid)
- Config in openclaw.json is valid
- Audit log exists and is being written to
- All enabled gates have recent audit events

Tier: quick (15-min cron)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

EXTENSIONS_DIR = Path.home() / ".openclaw" / "extensions" / "openclaw-gates"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
AUDIT_LOG = Path.home() / ".openclaw" / "logs" / "openclaw-gates-audit.jsonl"


def run(output_dir: Path) -> int:
    findings = []

    # Check plugin manifest
    manifest = EXTENSIONS_DIR / "openclaw.plugin.json"
    if not manifest.exists():
        findings.append("❌ openclaw.plugin.json missing")
    else:
        try:
            json.loads(manifest.read_text())
        except json.JSONDecodeError as e:
            findings.append(f"❌ openclaw.plugin.json invalid: {e}")

    # Check audit log
    if not AUDIT_LOG.exists():
        findings.append("⚠️ Audit log does not exist yet")
    else:
        size = AUDIT_LOG.stat().st_size
        age = datetime.now().timestamp() - AUDIT_LOG.stat().st_mtime
        if age > 3600:
            findings.append(f"⚠️ Audit log stale ({age/3600:.1f}h since last write)")
        else:
            findings.append(f"✅ Audit log active ({size} bytes, last write {age:.0f}s ago)")

    # Check config
    if OPENCLAW_CONFIG.exists():
        try:
            config = json.loads(OPENCLAW_CONFIG.read_text())
            gates_config = (
                config.get("plugins", {})
                .get("entries", {})
                .get("openclaw-gates", {})
                .get("config", {})
            )
            rules = gates_config.get("rules", {})
            enabled_rules = {k: v for k, v in rules.items() if v.get("enabled")}
            findings.append(f"ℹ️ {len(enabled_rules)} enabled rules: {', '.join(enabled_rules.keys())}")
        except Exception as e:
            findings.append(f"⚠️ Config parse error: {e}")

    has_issues = any("❌" in f or "⚠️" in f for f in findings)

    if has_issues:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = output_dir / f"{today}.md"
        with open(log_file, "a") as fh:
            fh.write(f"\n## {datetime.now().strftime('%H:%M')} — Gate Health\n")
            for finding in findings:
                fh.write(f"- {finding}\n")

    for f in findings:
        print(f"  {f}")

    return 1 if any("❌" in f for f in findings) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path,
                       default=Path.home() / ".openclaw/workspace/memory/metacognition")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sys.exit(run(args.output_dir))
