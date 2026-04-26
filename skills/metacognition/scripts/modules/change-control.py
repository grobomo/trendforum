#!/usr/bin/env python3
"""Module: change-control — Gate deployment change control monitor.

Delegates to the UNIFIED APPROVAL PIPELINE for all evidence checking
and status tracking. This module is now a thin wrapper that:

1. Syncs current gates from openclaw.json into the pipeline
2. Queries the pipeline for each gate's status
3. Reports findings in metacognition output format

The unified pipeline (approval-pipeline/pipeline.py) is the single
source of truth for approval status of both gates and metacog modules.

Tier: quick (15-min cron)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add approval-pipeline to path
WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE / "approval-pipeline"))

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"

# Try to import unified pipeline
try:
    from pipeline import ApprovalPipeline, EvidenceConfig
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False


def load_gate_configs() -> dict:
    """Load all gate configs from openclaw.json."""
    if not OPENCLAW_JSON.exists():
        return {}

    with open(OPENCLAW_JSON) as f:
        cfg = json.load(f)

    gates = {}
    oc_gates = (cfg.get("plugins", {}).get("entries", {})
                .get("openclaw-gates", {}).get("config", {}))

    # Named gates
    named_map = {
        "researchGate": "research-gate",
        "todoGate": "todo-gate",
        "changeControl": "change-control",
        "configSafety": "config-safety",
        "threadFidelity": "thread-fidelity",
        "projectScoping": "project-scoping",
    }
    for config_key, gate_name in named_map.items():
        g = oc_gates.get(config_key, {})
        if g.get("enabled"):
            gates[gate_name] = {
                "mode": g.get("mode", "log"),
                "plugin": "openclaw-gates",
                "config_path": f"plugins.entries.openclaw-gates.config.{config_key}",
            }

    # Static rules
    rules = oc_gates.get("rules", {})
    for rule_name, rule_cfg in rules.items():
        if rule_cfg.get("enabled"):
            gates[rule_name] = {
                "mode": rule_cfg.get("mode", "enforce"),
                "plugin": "openclaw-gates",
                "config_path": f"plugins.entries.openclaw-gates.config.rules.{rule_name}",
            }

    return gates


def run_with_pipeline(output_dir: Path):
    """Run using the unified approval pipeline."""
    pipeline = ApprovalPipeline()
    gates = load_gate_configs()
    now = datetime.now(timezone.utc)

    # Get per-gate overrides from env
    gate_overrides = {}
    try:
        raw = os.environ.get("METACOG_GATE_OVERRIDES", "{}")
        gate_overrides = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    default_min_hours = float(os.environ.get("METACOG_DEFAULT_MIN_MONITORING_HOURS", "24"))
    default_min_events = int(os.environ.get("METACOG_DEFAULT_MIN_TRIGGER_EVENTS", "20"))

    findings = []

    for gate_name, gate_info in gates.items():
        item_id = f"gate:{gate_name}"
        override = gate_overrides.get(gate_name, {})
        min_hours = override.get("minHours", default_min_hours)
        min_events = override.get("minEvents", default_min_events)

        # Submit to pipeline if not tracked
        ec = EvidenceConfig(
            min_monitoring_hours=min_hours,
            min_trigger_events=min_events,
        )
        pipeline.submit(
            item_id,
            kind="gate",
            display_name=f"{gate_name} ({gate_info['mode']})",
            evidence_config=ec,
            metadata={"current_mode": gate_info["mode"]},
        )

        # Check pipeline status
        result = pipeline.check(item_id)

        finding = {
            "gate": gate_name,
            "mode": gate_info["mode"],
            "plugin": gate_info["plugin"],
            "pipeline_stage": result.stage,
            "pipeline_ready": result.ready,
            "audit_events": result.evidence.event_count,
            "oldest_event": result.evidence.oldest_event,
            "newest_event": result.evidence.newest_event,
            "would_block_count": result.evidence.would_block_count,
            "blocked_count": result.evidence.blocked_count,
            "monitoring_hours": round(result.evidence.monitoring_hours, 1),
            "thresholds": {"minHours": min_hours, "minEvents": min_events},
            "status": "ok",
            "findings": [],
        }

        # Map pipeline status to human-readable findings
        if gate_info["mode"] == "enforce":
            if result.stage != "approved" and not pipeline.is_exempt(item_id):
                if result.evidence.event_count == 0:
                    finding["status"] = "critical"
                    finding["findings"].append(
                        "Gate in ENFORCE mode with ZERO audit evidence. "
                        "Deployed directly to enforce without log-mode monitoring."
                    )
                else:
                    finding["status"] = "warning"
                    finding["findings"].append(
                        f"Gate in ENFORCE mode but pipeline stage is '{result.stage}'. "
                        f"Reason: {result.reason}"
                    )
        elif gate_info["mode"] == "log":
            if result.ready and result.stage == "pending-approval":
                finding["status"] = "ready"
                finding["findings"].append(
                    f"Ready for promotion: {result.evidence.event_count} events "
                    f"over {result.evidence.monitoring_hours:.1f}h. "
                    f"Pipeline says: {result.reason}"
                )

        findings.append(finding)

    # Build summary
    summary = {
        "timestamp": now.isoformat(),
        "module": "change-control",
        "pipeline": "unified (approval-pipeline/pipeline.py)",
        "gates_assessed": len(findings),
        "warnings": sum(1 for f in findings if f["status"] == "warning"),
        "critical": sum(1 for f in findings if f["status"] == "critical"),
        "ready_to_enforce": sum(1 for f in findings if f["status"] == "ready"),
        "findings": findings,
        "sop": {
            "deploy": "New gates → always deploy in 'log' mode",
            "monitor": f"Minimum {default_min_hours}h and {default_min_events} events before enforce",
            "review": "Review would-block counts and false positive rate",
            "promote": "Flip to 'enforce' only after pipeline approval",
            "pipeline": "All approvals tracked in ~/.openclaw/state/approval-pipeline.json",
        },
    }

    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"change-control-{now.strftime('%Y-%m-%d')}.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    # Print human-readable
    print(f"\n=== Change Control Assessment ({now.strftime('%Y-%m-%d %H:%M UTC')}) ===")
    print(f"Pipeline: unified (approval-pipeline/pipeline.py)")
    print(f"Gates assessed: {len(findings)}")

    for f in findings:
        status_icon = {"ok": "✅", "warning": "⚠️", "critical": "🚨", "ready": "🟢"}.get(f["status"], "❓")
        pipe_icon = {"approved": "✅", "monitoring": "👁️", "pending-approval": "⏳",
                     "suspended": "🚨"}.get(f["pipeline_stage"], "?")
        print(f"\n{status_icon} {f['gate']} [{f['mode']}] — {f['audit_events']} events — pipeline: {pipe_icon} {f['pipeline_stage']}")
        for note in f["findings"]:
            print(f"   → {note}")

    if summary["critical"] > 0:
        print(f"\n🚨 {summary['critical']} CRITICAL: Gates deployed to enforce without monitoring!")
    elif summary["warnings"] > 0:
        print(f"\n⚠️  {summary['warnings']} warnings — some gates may need more monitoring.")
    elif summary["ready_to_enforce"] > 0:
        print(f"\n🟢 {summary['ready_to_enforce']} gate(s) ready to consider promoting to enforce mode.")
    else:
        print("\n✅ All gates following proper change control.")


def main():
    parser = argparse.ArgumentParser(description="Change control metacognition module")
    parser.add_argument("--output-dir", required=True, help="Output directory for findings")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if not PIPELINE_AVAILABLE:
        print("⚠️  Unified approval pipeline not available (approval-pipeline/pipeline.py)")
        print("   Change control module requires the pipeline. Exiting.")
        sys.exit(1)

    run_with_pipeline(output_dir)


if __name__ == "__main__":
    main()
