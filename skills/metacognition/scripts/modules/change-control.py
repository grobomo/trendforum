#!/usr/bin/env python3
"""Module: change-control — Gate deployment change control monitor.

Analyzes gate deployments to ensure proper change control:
1. New gates should deploy in "log" mode first
2. Must have monitoring evidence before flipping to "enforce"
3. Flags gates that were deployed directly to enforce (or flipped too fast)

Reads:
  - openclaw.json plugin config (gate modes)
  - audit logs (openclaw-gates-audit.jsonl, audit-logger.jsonl)
  - git log for config changes

Outputs:
  - Findings to metacognition daily file
  - JSON summary to output-dir

Tier: quick (15-min cron)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"
LOGS_DIR = Path.home() / ".openclaw" / "logs"
WORKSPACE = Path.home() / ".openclaw" / "workspace"

# Audit log files to check for evidence
AUDIT_LOGS = [
    LOGS_DIR / "openclaw-gates-audit.jsonl",
    LOGS_DIR / "audit-logger.jsonl",
]

# Default thresholds — can be overridden per-gate via config
DEFAULT_MIN_MONITORING_HOURS = int(os.environ.get("METACOG_DEFAULT_MIN_MONITORING_HOURS", "24"))
DEFAULT_MIN_TRIGGER_EVENTS = int(os.environ.get("METACOG_DEFAULT_MIN_TRIGGER_EVENTS", "20"))

# Per-gate overrides (JSON string from env, e.g. '{"change-control": {"minHours": 4, "minEvents": 10}}')
GATE_OVERRIDES = {}
try:
    _raw = os.environ.get("METACOG_GATE_OVERRIDES", "{}")
    GATE_OVERRIDES = json.loads(_raw)
except (json.JSONDecodeError, ValueError):
    pass


def load_gate_configs() -> dict:
    """Load all gate configs from openclaw.json."""
    if not OPENCLAW_JSON.exists():
        return {}
    
    with open(OPENCLAW_JSON) as f:
        cfg = json.load(f)
    
    gates = {}
    
    # Check openclaw-gates plugin
    oc_gates = (cfg.get("plugins", {}).get("entries", {})
                .get("openclaw-gates", {}).get("config", {}))
    
    # Research gate
    rg = oc_gates.get("researchGate", {})
    if rg.get("enabled"):
        gates["research-gate"] = {
            "mode": rg.get("mode", "log"),
            "plugin": "openclaw-gates",
            "config_path": "plugins.entries.openclaw-gates.config.researchGate",
        }
    
    # Todo gate
    tg = oc_gates.get("todoGate", {})
    if tg.get("enabled"):
        gates["todo-gate"] = {
            "mode": tg.get("mode", "log"),
            "plugin": "openclaw-gates",
            "config_path": "plugins.entries.openclaw-gates.config.todoGate",
        }
    
    # Static rules
    rules = oc_gates.get("rules", {})
    for rule_name, rule_cfg in rules.items():
        if rule_cfg.get("enabled"):
            gates[f"rule:{rule_name}"] = {
                "mode": rule_cfg.get("mode", "enforce"),
                "plugin": "openclaw-gates",
                "config_path": f"plugins.entries.openclaw-gates.config.rules.{rule_name}",
            }
    
    return gates


def count_audit_events(gate_id: str) -> dict:
    """Count audit log events for a specific gate, with timestamps."""
    events = {"total": 0, "oldest": None, "newest": None, "would_block": 0, "blocked": 0}
    
    # Map gate ID to what appears in audit logs
    rule_id_patterns = [gate_id, f"_{gate_id}"]
    
    for log_path in AUDIT_LOGS:
        if not log_path.exists():
            continue
        try:
            with open(log_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except (json.JSONDecodeError, ValueError):
                        continue
                    
                    rule_id = entry.get("ruleId", "")
                    # Check if this entry relates to our gate
                    if not any(p in rule_id for p in rule_id_patterns):
                        continue
                    
                    events["total"] += 1
                    ts = entry.get("timestamp") or entry.get("ts")
                    if ts:
                        if events["oldest"] is None or ts < events["oldest"]:
                            events["oldest"] = ts
                        if events["newest"] is None or ts > events["newest"]:
                            events["newest"] = ts
                    
                    result = entry.get("result", "")
                    if "would_block" in result:
                        events["would_block"] += 1
                    elif "block" in result:
                        events["blocked"] += 1
        except Exception:
            continue
    
    return events


def get_recent_config_changes() -> list:
    """Check git log for recent config changes to gate modes."""
    changes = []
    try:
        # Check workspace git log for openclaw.json changes
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=7 days ago", "-20",
             "--", "*.json", "*.yaml", "*.ts"],
            cwd=str(WORKSPACE),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if any(kw in line.lower() for kw in [
                    "gate", "enforce", "log", "mode", "guardrail", "openclaw-gates"
                ]):
                    changes.append(line.strip())
    except Exception:
        pass
    
    return changes


def assess_gate(gate_id: str, gate_info: dict) -> dict:
    """Assess change control posture for a single gate."""
    mode = gate_info["mode"]
    audit = count_audit_events(gate_id)
    
    # Resolve per-gate thresholds
    override = GATE_OVERRIDES.get(gate_id, {})
    min_hours = override.get("minHours", DEFAULT_MIN_MONITORING_HOURS)
    min_events = override.get("minEvents", DEFAULT_MIN_TRIGGER_EVENTS)
    
    finding = {
        "gate": gate_id,
        "mode": mode,
        "plugin": gate_info["plugin"],
        "audit_events": audit["total"],
        "oldest_event": audit["oldest"],
        "newest_event": audit["newest"],
        "would_block_count": audit["would_block"],
        "blocked_count": audit["blocked"],
        "thresholds": {"minHours": min_hours, "minEvents": min_events},
        "status": "ok",
        "findings": [],
    }
    
    if mode == "enforce":
        # Check if there's enough monitoring evidence
        if audit["total"] < min_events:
            finding["status"] = "warning"
            finding["findings"].append(
                f"Gate is in ENFORCE mode but only has {audit['total']} audit events "
                f"(minimum: {min_events}). Was log-mode monitoring sufficient?"
            )
        
        if audit["oldest"]:
            try:
                oldest_dt = datetime.fromisoformat(audit["oldest"].replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - oldest_dt).total_seconds() / 3600
                if age_hours < min_hours:
                    finding["status"] = "warning"
                    finding["findings"].append(
                        f"Gate in ENFORCE mode but monitoring history is only {age_hours:.1f}h old "
                        f"(minimum: {min_hours}h). Flipped to enforce too quickly?"
                    )
            except (ValueError, TypeError):
                pass
        elif audit["total"] == 0:
            finding["status"] = "critical"
            finding["findings"].append(
                "Gate is in ENFORCE mode with ZERO audit evidence. "
                "This gate was likely deployed directly to enforce without any log-mode monitoring."
            )
    
    elif mode == "log":
        # Log mode is fine — just report readiness
        if audit["total"] >= min_events and audit["oldest"]:
            try:
                oldest_dt = datetime.fromisoformat(audit["oldest"].replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - oldest_dt).total_seconds() / 3600
                if age_hours >= min_hours:
                    finding["status"] = "ready"
                    finding["findings"].append(
                        f"Gate has {audit['total']} events over {age_hours:.1f}h. "
                        f"Ready to consider flipping to enforce mode. "
                        f"({audit['would_block_count']} would-block events found.)"
                    )
            except (ValueError, TypeError):
                pass
    
    return finding


def main():
    parser = argparse.ArgumentParser(description="Change control metacognition module")
    parser.add_argument("--output-dir", required=True, help="Output directory for findings")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    gates = load_gate_configs()
    config_changes = get_recent_config_changes()
    
    findings = []
    for gate_id, gate_info in gates.items():
        finding = assess_gate(gate_id, gate_info)
        findings.append(finding)
    
    # Build summary
    summary = {
        "timestamp": now.isoformat(),
        "module": "change-control",
        "gates_assessed": len(findings),
        "warnings": sum(1 for f in findings if f["status"] == "warning"),
        "critical": sum(1 for f in findings if f["status"] == "critical"),
        "ready_to_enforce": sum(1 for f in findings if f["status"] == "ready"),
        "recent_config_changes": config_changes,
        "findings": findings,
        "sop": {
            "deploy": "New gates → always deploy in 'log' mode",
            "monitor": f"Minimum {MIN_MONITORING_HOURS}h and {MIN_TRIGGER_EVENTS} events before enforce",
            "review": "Review would-block counts and false positive rate",
            "promote": "Flip to 'enforce' only after validation",
        },
    }
    
    # Write JSON output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"change-control-{now.strftime('%Y-%m-%d')}.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    
    # Print human-readable summary
    if not args.json:
        print(f"\n=== Change Control Assessment ({now.strftime('%Y-%m-%d %H:%M UTC')}) ===")
        print(f"Gates assessed: {len(findings)}")
        
        for f in findings:
            status_icon = {"ok": "✅", "warning": "⚠️", "critical": "🚨", "ready": "🟢"}.get(f["status"], "❓")
            print(f"\n{status_icon} {f['gate']} [{f['mode']}] — {f['audit_events']} audit events")
            for note in f["findings"]:
                print(f"   → {note}")
        
        if config_changes:
            print(f"\n📋 Recent gate-related config changes:")
            for c in config_changes[:5]:
                print(f"   {c}")
        
        if summary["critical"] > 0:
            print(f"\n🚨 {summary['critical']} CRITICAL: Gates deployed to enforce without monitoring!")
        elif summary["warnings"] > 0:
            print(f"\n⚠️  {summary['warnings']} warnings — some gates may need more monitoring.")
        elif summary["ready_to_enforce"] > 0:
            print(f"\n🟢 {summary['ready_to_enforce']} gate(s) ready to consider promoting to enforce mode.")
        else:
            print("\n✅ All gates following proper change control.")
    else:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
