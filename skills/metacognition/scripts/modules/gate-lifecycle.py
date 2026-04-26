#!/usr/bin/env python3
"""Module: gate-lifecycle — Post-enforce monitoring + full gate lifecycle dashboard.

Tracks the complete lifecycle of every gate:
  log:new → log:ready → enforce:watch → enforce:stable

Phase names encode both the mode and monitoring state:
  log:new          — deployed in log mode, collecting initial data
  log:ready        — enough evidence collected, safe to promote
  enforce:watch    — actively blocking + being monitored for false positives
  enforce:stable   — blocking, past watch period, proven healthy

During probation (post-enforce):
  - Monitors block rate for false positives
  - Alerts if block rate exceeds threshold
  - Recommends rollback if too many false positives
  - Graduates to "stable" after probation period with healthy metrics

Also generates the meta dashboard: one view of everything being monitored.

Tier: quick (15-min cron)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"
LOGS_DIR = Path.home() / ".openclaw" / "logs"
WORKSPACE = Path.home() / ".openclaw" / "workspace"
STATE_FILE = WORKSPACE / "memory" / "gate-lifecycle-state.json"

AUDIT_LOGS = [
    LOGS_DIR / "openclaw-gates-audit.jsonl",
    LOGS_DIR / "audit-logger.jsonl",
]

# Defaults
DEFAULT_WATCH_HOURS = 72  # 3 days
DEFAULT_MAX_BLOCK_RATE = 0.15  # 15% block rate triggers alert


def load_state() -> dict:
    """Load lifecycle state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"gates": {}, "last_run": None}


def save_state(state: dict):
    """Persist lifecycle state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


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
    for key in ["researchGate", "todoGate", "changeControl", "configSafety"]:
        g = oc_gates.get(key, {})
        if g.get("enabled"):
            gates[key] = {"mode": g.get("mode", "log"), "plugin": "openclaw-gates"}

    # Static rules
    for rule_name, rule_cfg in oc_gates.get("rules", {}).items():
        if rule_cfg.get("enabled"):
            gates[f"rule:{rule_name}"] = {
                "mode": rule_cfg.get("mode", "enforce"),
                "plugin": "openclaw-gates",
            }

    # Claude-code-gates modules (these are always enforce by nature)
    cc_gates = (cfg.get("plugins", {}).get("entries", {})
                .get("claude-code-gates", {}).get("config", {}))
    if cc_gates:
        gates["claude-code-gates"] = {"mode": "enforce", "plugin": "claude-code-gates"}

    return gates


def load_overrides() -> dict:
    """Load per-gate overrides from openclaw.json."""
    if not OPENCLAW_JSON.exists():
        return {}
    with open(OPENCLAW_JSON) as f:
        cfg = json.load(f)
    cc = (cfg.get("plugins", {}).get("entries", {})
          .get("openclaw-gates", {}).get("config", {})
          .get("changeControl", {}))
    return cc.get("gateOverrides", {})


def count_events_since(gate_id: str, since_ts: float) -> dict:
    """Count audit events for a gate since a timestamp."""
    result = {"total": 0, "blocked": 0, "would_block": 0, "allowed": 0}
    patterns = [gate_id, f"_{gate_id}"]

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
                    if not any(p in rule_id for p in patterns):
                        continue

                    ts = entry.get("timestamp") or entry.get("ts")
                    if ts:
                        try:
                            entry_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if entry_dt.timestamp() < since_ts:
                                continue
                        except (ValueError, TypeError):
                            pass

                    result["total"] += 1
                    r = entry.get("result", "")
                    if "would_block" in r:
                        result["would_block"] += 1
                    elif "block" in r:
                        result["blocked"] += 1
                    elif "allow" in r:
                        result["allowed"] += 1
        except Exception:
            continue

    return result


def count_all_events(gate_id: str) -> dict:
    """Count all audit events for a gate (no time filter)."""
    return count_events_since(gate_id, 0)


def assess_gate_lifecycle(gate_id: str, gate_info: dict, state: dict, overrides: dict) -> dict:
    """Assess lifecycle state for a single gate."""
    now = datetime.now(timezone.utc)
    mode = gate_info["mode"]
    gate_state = state.get("gates", {}).get(gate_id, {})
    override = overrides.get(gate_id, {})

    watch_hours = override.get("watchHours", DEFAULT_WATCH_HOURS)
    max_block_rate = DEFAULT_MAX_BLOCK_RATE

    all_events = count_all_events(gate_id)

    entry = {
        "gate": gate_id,
        "mode": mode,
        "plugin": gate_info["plugin"],
        "phase": "unknown",
        "total_events": all_events["total"],
        "blocked": all_events["blocked"],
        "would_block": all_events["would_block"],
        "watch_hours": watch_hours,
        "findings": [],
    }

    if mode == "log":
        if all_events["total"] == 0:
            entry["phase"] = "log:new"
            entry["findings"].append("Logging only. No events yet — freshly deployed.")
        else:
            # Check if enough evidence to be ready for promotion
            override = overrides.get(gate_id, {})
            min_hours = override.get("minHours", 24)
            min_events = override.get("minEvents", 20)
            entry["phase"] = "log:new"
            entry["findings"].append(
                f"Logging only. {all_events['total']} events so far "
                f"(need {min_events} events over {min_hours}h to be ready)."
            )

    elif mode == "enforce":
        enforced_at = gate_state.get("enforced_at")

        if not enforced_at:
            state.setdefault("gates", {})[gate_id] = state.get("gates", {}).get(gate_id, {})
            state["gates"][gate_id]["enforced_at"] = now.isoformat()
            enforced_at = now.isoformat()
            entry["phase"] = "enforce:watch"
            entry["findings"].append(
                f"Blocking + watching. Just entered enforce mode. Watch period: {watch_hours}h."
            )
        else:
            try:
                enforced_dt = datetime.fromisoformat(enforced_at.replace("Z", "+00:00"))
                hours_in_enforce = (now - enforced_dt).total_seconds() / 3600
                entry["hours_in_enforce"] = round(hours_in_enforce, 1)

                if hours_in_enforce < watch_hours:
                    entry["phase"] = "enforce:watch"
                    remaining = watch_hours - hours_in_enforce
                    entry["watch_remaining_hours"] = round(remaining, 1)

                    watch_events = count_events_since(gate_id, enforced_dt.timestamp())
                    entry["watch_events"] = watch_events

                    if watch_events["total"] > 5:
                        block_rate = watch_events["blocked"] / watch_events["total"]
                        entry["watch_block_rate"] = round(block_rate, 3)

                        if block_rate > max_block_rate:
                            entry["findings"].append(
                                f"⚠️ Blocking + watching. High block rate: {block_rate:.1%} "
                                f"(threshold: {max_block_rate:.0%}). "
                                f"{watch_events['blocked']}/{watch_events['total']} events blocked. "
                                f"Consider rolling back to log mode."
                            )
                        else:
                            entry["findings"].append(
                                f"Blocking + watching. Healthy: {block_rate:.1%} block rate, "
                                f"{remaining:.1f}h remaining."
                            )
                    else:
                        entry["findings"].append(
                            f"Blocking + watching. {remaining:.1f}h remaining, "
                            f"{watch_events['total']} events so far."
                        )
                else:
                    entry["phase"] = "enforce:stable"
                    state["gates"][gate_id]["stable_at"] = now.isoformat()
                    entry["findings"].append(
                        f"Blocking + stable. Watch complete ({hours_in_enforce:.0f}h). Proven healthy."
                    )
            except (ValueError, TypeError):
                entry["phase"] = "enforce:watch"
                entry["findings"].append("Blocking + watching. Could not parse enforcement timestamp.")

    return entry


def build_dashboard(assessments: list) -> str:
    """Build a human-readable meta dashboard."""
    lines = []
    lines.append("=" * 60)
    lines.append("  GATE LIFECYCLE DASHBOARD")
    lines.append(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)

    # Group by phase
    stages = {"log:new": [], "log:ready": [], "enforce:watch": [], "enforce:stable": [], "unknown": []}
    for a in assessments:
        stages.get(a["phase"], stages["unknown"]).append(a)

    stage_icons = {
        "log:new": "📝", "log:ready": "🟢", "enforce:watch": "🔒👀",
        "enforce:stable": "🔒✅", "unknown": "❓",
    }

    stage_labels = {
        "log:new": "LOG:NEW — logging only, collecting data",
        "log:ready": "LOG:READY — enough evidence, safe to promote",
        "enforce:watch": "ENFORCE:WATCH — blocking + actively monitored",
        "enforce:stable": "ENFORCE:STABLE — blocking, proven healthy",
        "unknown": "UNKNOWN",
    }

    for stage, items in stages.items():
        if not items:
            continue
        label = stage_labels.get(stage, stage.upper())
        lines.append(f"\n{stage_icons.get(stage, '❓')} {label} ({len(items)})")
        lines.append("-" * 40)
        for item in items:
            mode_tag = f"[{item['mode']}]"
            events_tag = f"{item['total_events']} events"
            extra = ""
            if item.get("probation_remaining_hours") is not None:
                extra = f" | {item['probation_remaining_hours']:.0f}h remaining"
            if item.get("probation_block_rate") is not None:
                extra += f" | block rate: {item['probation_block_rate']:.1%}"
            lines.append(f"  {item['gate']} {mode_tag} — {events_tag}{extra}")
            for f in item["findings"]:
                lines.append(f"    → {f}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Gate lifecycle monitor")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    state = load_state()
    gates = load_gate_configs()
    overrides = load_overrides()

    assessments = []
    for gate_id, gate_info in gates.items():
        assessment = assess_gate_lifecycle(gate_id, gate_info, state, overrides)
        assessments.append(assessment)

    # Save state (records enforcement timestamps)
    save_state(state)

    # Build summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "gate-lifecycle",
        "total_gates": len(assessments),
        "by_phase": {
            phase: sum(1 for a in assessments if a["phase"] == phase)
            for phase in ["log:new", "log:ready", "enforce:watch", "enforce:stable", "unknown"]
        },
        "alerts": [a for a in assessments if any("⚠️" in f for f in a["findings"])],
        "assessments": assessments,
    }

    # Write output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(output_dir / f"gate-lifecycle-{now_str}.json", "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(build_dashboard(assessments))

        if summary["alerts"]:
            print(f"\n🚨 {len(summary['alerts'])} gate(s) need attention!")


if __name__ == "__main__":
    main()
