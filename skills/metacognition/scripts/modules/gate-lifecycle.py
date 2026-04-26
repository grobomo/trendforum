#!/usr/bin/env python3
"""Module: gate-lifecycle — Gate lifecycle dashboard + monitoring.

Four phases, three MFA gates:

  New → Log-only → Enforcing → Trusted
        🔑 MFA      🔑 MFA      🔑 MFA

  New       — gate exists, not active. No MFA needed to create.
  Log-only  — monitoring without taking action. MFA to activate.
  Enforcing — taking action and monitoring. MFA to promote.
  Trusted   — monitoring period passed. MFA to graduate.

No automation can promote between phases — each transition requires
explicit human (Joel) approval.

Tier: quick (15-min cron)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"
LOGS_DIR = Path.home() / ".openclaw" / "logs"
WORKSPACE = Path.home() / ".openclaw" / "workspace"
STATE_FILE = WORKSPACE / "memory" / "gate-lifecycle-state.json"

AUDIT_LOGS = [
    LOGS_DIR / "openclaw-gates-audit.jsonl",
    LOGS_DIR / "audit-logger.jsonl",
]

DEFAULT_WATCH_HOURS = 72
DEFAULT_MAX_BLOCK_RATE = 0.15


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"gates": {}, "last_run": None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def load_gate_configs() -> dict:
    if not OPENCLAW_JSON.exists():
        return {}
    with open(OPENCLAW_JSON) as f:
        cfg = json.load(f)

    gates = {}
    oc_gates = (cfg.get("plugins", {}).get("entries", {})
                .get("openclaw-gates", {}).get("config", {}))

    for key in ["researchGate", "todoGate", "changeControl", "configSafety"]:
        g = oc_gates.get(key, {})
        if g.get("enabled"):
            gates[key] = {"mode": g.get("mode", "log"), "plugin": "openclaw-gates"}

    for rule_name, rule_cfg in oc_gates.get("rules", {}).items():
        if rule_cfg.get("enabled"):
            gates[f"rule:{rule_name}"] = {
                "mode": rule_cfg.get("mode", "enforce"),
                "plugin": "openclaw-gates",
            }

    return gates


def load_overrides() -> dict:
    if not OPENCLAW_JSON.exists():
        return {}
    with open(OPENCLAW_JSON) as f:
        cfg = json.load(f)
    cc = (cfg.get("plugins", {}).get("entries", {})
          .get("openclaw-gates", {}).get("config", {})
          .get("changeControl", {}))
    return cc.get("gateOverrides", {})


def count_events_since(gate_id: str, since_ts: float) -> dict:
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
    return count_events_since(gate_id, 0)


def assess_gate(gate_id: str, gate_info: dict, state: dict, overrides: dict) -> dict:
    now = datetime.now(timezone.utc)
    mode = gate_info["mode"]
    gate_state = state.get("gates", {}).get(gate_id, {})
    override = overrides.get(gate_id, {})
    watch_hours = override.get("watchHours", DEFAULT_WATCH_HOURS)
    max_block_rate = DEFAULT_MAX_BLOCK_RATE
    all_events = count_all_events(gate_id)

    entry = {
        "gate": gate_id,
        "plugin": gate_info["plugin"],
        "phase": "new",
        "total_events": all_events["total"],
        "blocked": all_events["blocked"],
        "would_block": all_events["would_block"],
        "findings": [],
    }

    if mode == "log":
        # Log-only: monitoring without taking action
        entry["phase"] = "log-only"
        if all_events["total"] == 0:
            entry["findings"].append("Monitoring, no events recorded yet.")
        else:
            entry["findings"].append(
                f"Monitoring: {all_events['total']} events, "
                f"{all_events['would_block']} would-block."
            )

    elif mode == "enforce":
        # Enforcing: taking action and monitoring
        enforced_at = gate_state.get("enforced_at")

        if not enforced_at:
            # First time seeing enforce — record timestamp
            state.setdefault("gates", {})[gate_id] = state.get("gates", {}).get(gate_id, {})
            state["gates"][gate_id]["enforced_at"] = now.isoformat()
            enforced_at = now.isoformat()

        try:
            enforced_dt = datetime.fromisoformat(enforced_at.replace("Z", "+00:00"))
            hours_in_enforce = (now - enforced_dt).total_seconds() / 3600
            entry["hours_in_enforce"] = round(hours_in_enforce, 1)

            # Check if graduated to trusted
            graduated_at = gate_state.get("trusted_at")
            if graduated_at:
                entry["phase"] = "trusted"
                entry["findings"].append(
                    f"Taking action. Monitoring period passed ({hours_in_enforce:.0f}h). "
                    f"Graduated {graduated_at[:10]}."
                )
            elif hours_in_enforce >= watch_hours:
                # Watch period elapsed — but NOT auto-graduated. Needs MFA.
                entry["phase"] = "enforcing"
                watch_events = count_events_since(gate_id, enforced_dt.timestamp())
                block_rate = (watch_events["blocked"] / watch_events["total"]
                              if watch_events["total"] > 0 else 0)
                entry["findings"].append(
                    f"Taking action + monitoring. Watch period elapsed ({hours_in_enforce:.0f}h >= {watch_hours}h). "
                    f"Block rate: {block_rate:.1%}. "
                    f"🔑 Ready for MFA approval to graduate to Trusted."
                )
            else:
                entry["phase"] = "enforcing"
                remaining = watch_hours - hours_in_enforce
                watch_events = count_events_since(gate_id, enforced_dt.timestamp())

                if watch_events["total"] > 5:
                    block_rate = watch_events["blocked"] / watch_events["total"]
                    entry["watch_block_rate"] = round(block_rate, 3)
                    if block_rate > max_block_rate:
                        entry["findings"].append(
                            f"⚠️ Taking action + monitoring. High block rate: {block_rate:.1%} "
                            f"({watch_events['blocked']}/{watch_events['total']}). "
                            f"Consider rolling back to Log-only."
                        )
                    else:
                        entry["findings"].append(
                            f"Taking action + monitoring. {remaining:.0f}h remaining. "
                            f"Block rate: {block_rate:.1%} (healthy)."
                        )
                else:
                    entry["findings"].append(
                        f"Taking action + monitoring. {remaining:.0f}h remaining, "
                        f"{watch_events['total']} events so far."
                    )
        except (ValueError, TypeError):
            entry["phase"] = "enforcing"
            entry["findings"].append("Taking action + monitoring. Could not parse timestamp.")

    else:
        # Not enabled or unknown mode
        entry["phase"] = "new"
        entry["findings"].append("Gate exists but is not active.")

    return entry


def build_dashboard(assessments: list) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  GATE LIFECYCLE DASHBOARD")
    lines.append(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("  New → Log-only → Enforcing → Trusted")
    lines.append("         🔑 MFA      🔑 MFA      🔑 MFA")
    lines.append("=" * 60)

    phases = {"new": [], "log-only": [], "enforcing": [], "trusted": []}
    for a in assessments:
        phases.get(a["phase"], phases["new"]).append(a)

    icons = {"new": "📋", "log-only": "📝", "enforcing": "🔒", "trusted": "🛡️"}
    descriptions = {
        "new": "NEW — exists, not active",
        "log-only": "LOG-ONLY — monitoring without taking action",
        "enforcing": "ENFORCING — taking action and monitoring",
        "trusted": "TRUSTED — monitoring period passed",
    }

    for phase, items in phases.items():
        if not items:
            continue
        icon = icons.get(phase, "❓")
        desc = descriptions.get(phase, phase.upper())
        lines.append(f"\n{icon} {desc} ({len(items)})")
        lines.append("-" * 50)
        for item in items:
            extra = ""
            if item.get("hours_in_enforce") is not None:
                extra = f" | {item['hours_in_enforce']}h in enforce"
            if item.get("watch_block_rate") is not None:
                extra += f" | block rate: {item['watch_block_rate']:.1%}"
            lines.append(f"  {item['gate']} — {item['total_events']} events{extra}")
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
        assessment = assess_gate(gate_id, gate_info, state, overrides)
        assessments.append(assessment)

    save_state(state)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "gate-lifecycle",
        "total_gates": len(assessments),
        "by_phase": {
            phase: sum(1 for a in assessments if a["phase"] == phase)
            for phase in ["new", "log-only", "enforcing", "trusted"]
        },
        "alerts": [a for a in assessments if any("⚠️" in f for f in a["findings"])],
        "mfa_ready": [a for a in assessments if any("🔑" in f for f in a["findings"])],
        "assessments": assessments,
    }

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
        if summary["mfa_ready"]:
            print(f"\n🔑 {len(summary['mfa_ready'])} gate(s) ready for MFA approval!")


if __name__ == "__main__":
    main()
