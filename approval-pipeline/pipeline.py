#!/usr/bin/env python3
"""Unified Approval Pipeline — single approval system for gates and metacog modules.

Provides a shared pipeline for anything that needs staged approval:
  1. Gate mode promotions (log → enforce)
  2. Metacog module activation (discover → monitor → approve)
  3. Future: MFA gates, config changes, plugin deployments

Pipeline stages:
  submitted → monitoring → pending-approval → approved → (suspended)

Evidence requirements (configurable per-item):
  - Minimum monitoring period (default: 24h)
  - Minimum trigger/run events (default: 20)
  - Static analysis clean (for modules)
  - Hash verification (for modules)

Consumers call into this module instead of implementing their own approval logic.

Usage:
    from pipeline import ApprovalPipeline

    pipeline = ApprovalPipeline()
    pipeline.submit("gate:research-gate", kind="gate", evidence_config={...})
    result = pipeline.check("gate:research-gate")
    # result.stage, result.ready, result.reason, result.evidence
"""

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Configuration ────────────────────────────────────────────────────────

PIPELINE_STATE_PATH = Path(os.environ.get(
    "APPROVAL_PIPELINE_STATE",
    str(Path.home() / ".openclaw" / "state" / "approval-pipeline.json"),
))

AUDIT_LOGS_DIR = Path.home() / ".openclaw" / "logs"
AUDIT_LOG_FILES = [
    AUDIT_LOGS_DIR / "openclaw-gates-audit.jsonl",
    AUDIT_LOGS_DIR / "audit-logger.jsonl",
]

# Default thresholds
DEFAULT_MIN_MONITORING_HOURS = 24
DEFAULT_MIN_TRIGGER_EVENTS = 20
DEFAULT_PROBATION_HOURS = 72
DEFAULT_MAX_PROBATION_BLOCK_RATE = 0.15

# Items that bypass monitoring (foundational safety — born enforce)
DEFAULT_EXEMPT = frozenset([
    "gate:bias-to-action",
    "gate:archive-before-delete",
    "gate:emergency-shutoff",
])


# ── Data Types ───────────────────────────────────────────────────────────

@dataclass
class EvidenceConfig:
    """Per-item evidence requirements."""
    min_monitoring_hours: float = DEFAULT_MIN_MONITORING_HOURS
    min_trigger_events: int = DEFAULT_MIN_TRIGGER_EVENTS
    probation_hours: float = DEFAULT_PROBATION_HOURS
    max_block_rate: float = DEFAULT_MAX_PROBATION_BLOCK_RATE
    require_clean_static: bool = False  # For modules
    require_hash_match: bool = False    # For modules
    rationale: str = ""


@dataclass
class Evidence:
    """Collected evidence for an item."""
    event_count: int = 0
    oldest_event: Optional[str] = None
    newest_event: Optional[str] = None
    monitoring_hours: float = 0.0
    would_block_count: int = 0
    blocked_count: int = 0
    monitoring_runs: int = 0
    static_analysis_clean: Optional[bool] = None
    hash_verified: Optional[bool] = None
    hash_expected: Optional[str] = None
    hash_current: Optional[str] = None


@dataclass
class ApprovalItem:
    """An item tracked in the approval pipeline."""
    item_id: str
    kind: str  # "gate" | "module" | "config" | ...
    display_name: str = ""
    stage: str = "submitted"  # submitted | monitoring | pending-approval | approved | suspended
    submitted_at: Optional[str] = None
    monitoring_started: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    suspended_at: Optional[str] = None
    suspend_reason: Optional[str] = None
    evidence_config: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)  # Kind-specific data


@dataclass
class CheckResult:
    """Result of checking an item's approval status."""
    item_id: str
    stage: str
    ready: bool  # Ready to advance to next stage
    reason: str
    evidence: Evidence
    next_stage: Optional[str] = None


# ── Pipeline ─────────────────────────────────────────────────────────────

class ApprovalPipeline:
    """Unified approval pipeline for gates, modules, and future consumers."""

    def __init__(self, state_path: Optional[Path] = None, exempt: Optional[set] = None):
        self.state_path = state_path or PIPELINE_STATE_PATH
        self.exempt = exempt if exempt is not None else set(DEFAULT_EXEMPT)
        self._state = self._load_state()

    def _load_state(self) -> dict:
        """Load pipeline state from disk."""
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError):
                pass
        return {"items": {}, "audit_trail": [], "version": 1}

    def _save_state(self):
        """Persist pipeline state."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_path, "w") as f:
            json.dump(self._state, f, indent=2, default=str)
            f.write("\n")

    def _audit(self, action: str, item_id: str, detail: str = ""):
        """Append to audit trail."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "item_id": item_id,
            "detail": detail,
        }
        trail = self._state.setdefault("audit_trail", [])
        trail.append(entry)
        # Keep last 500 entries
        if len(trail) > 500:
            self._state["audit_trail"] = trail[-500:]

    def is_exempt(self, item_id: str) -> bool:
        """Check if an item is exempt from approval pipeline."""
        return item_id in self.exempt

    # ── Submit ─────────────────────────────────────────────────

    def submit(
        self,
        item_id: str,
        kind: str,
        display_name: str = "",
        evidence_config: Optional[EvidenceConfig] = None,
        metadata: Optional[dict] = None,
        auto_monitor: bool = True,
    ) -> ApprovalItem:
        """Submit an item to the approval pipeline.
        
        If the item already exists and is approved, returns it as-is.
        If auto_monitor is True, immediately advances to monitoring stage.
        """
        if self.is_exempt(item_id):
            # Exempt items are auto-approved
            item = ApprovalItem(
                item_id=item_id,
                kind=kind,
                display_name=display_name or item_id,
                stage="approved",
                submitted_at=datetime.now(timezone.utc).isoformat(),
                approved_at=datetime.now(timezone.utc).isoformat(),
                approved_by="exempt",
            )
            self._state["items"][item_id] = asdict(item)
            self._audit("auto-approved", item_id, "exempt item")
            self._save_state()
            return item

        existing = self._state["items"].get(item_id)
        if existing and existing.get("stage") == "approved":
            return self._dict_to_item(existing)

        now = datetime.now(timezone.utc).isoformat()
        ec = evidence_config or EvidenceConfig()

        item = ApprovalItem(
            item_id=item_id,
            kind=kind,
            display_name=display_name or item_id,
            stage="monitoring" if auto_monitor else "submitted",
            submitted_at=now,
            monitoring_started=now if auto_monitor else None,
            evidence_config=asdict(ec),
            metadata=metadata or {},
        )
        self._state["items"][item_id] = asdict(item)
        self._audit("submitted", item_id, f"kind={kind}, auto_monitor={auto_monitor}")
        self._save_state()
        return item

    # ── Evidence Collection ────────────────────────────────────

    def collect_audit_evidence(self, item_id: str) -> Evidence:
        """Collect evidence from audit logs for a given item.
        
        Works for both gates and modules by matching against the item_id
        and its base name in audit log entries.
        """
        evidence = Evidence()
        
        # Build search patterns from item_id
        # "gate:research-gate" → ["research-gate", "_research-gate", "research_gate"]
        # "module:openclaw-gates/gate-health" → ["gate-health", "openclaw-gates/gate-health"]
        base_name = item_id.split(":", 1)[-1] if ":" in item_id else item_id
        short_name = base_name.split("/")[-1] if "/" in base_name else base_name
        patterns = [base_name, short_name, f"_{short_name}"]

        for log_path in AUDIT_LOG_FILES:
            if not log_path.exists():
                continue
            try:
                with open(log_path) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue

                        rule_id = entry.get("ruleId", "") or entry.get("module", "")
                        if not any(p in rule_id for p in patterns):
                            continue

                        evidence.event_count += 1
                        ts = entry.get("timestamp") or entry.get("ts")
                        if ts:
                            if evidence.oldest_event is None or ts < evidence.oldest_event:
                                evidence.oldest_event = ts
                            if evidence.newest_event is None or ts > evidence.newest_event:
                                evidence.newest_event = ts

                        result = entry.get("result", "")
                        if "would_block" in str(result):
                            evidence.would_block_count += 1
                        elif "block" in str(result):
                            evidence.blocked_count += 1
            except Exception:
                continue

        # Calculate monitoring hours
        item_data = self._state["items"].get(item_id, {})
        monitoring_started = item_data.get("monitoring_started")
        if monitoring_started:
            try:
                start_dt = datetime.fromisoformat(monitoring_started.replace("Z", "+00:00"))
                evidence.monitoring_hours = (
                    datetime.now(timezone.utc) - start_dt
                ).total_seconds() / 3600
            except (ValueError, TypeError):
                pass

        return evidence

    def record_module_run(self, item_id: str, findings: list = None):
        """Record a monitoring run for a module."""
        item = self._state["items"].get(item_id)
        if not item:
            return
        
        evidence = item.setdefault("evidence", {})
        evidence["monitoring_runs"] = evidence.get("monitoring_runs", 0) + 1
        if findings:
            existing = evidence.get("monitoring_findings", [])
            existing.extend(findings[-5:])  # Keep last 5 findings per run
            evidence["monitoring_findings"] = existing[-20:]  # Cap at 20 total
        
        self._save_state()

    def set_static_analysis(self, item_id: str, clean: bool, details: str = ""):
        """Record static analysis result for a module."""
        item = self._state["items"].get(item_id)
        if not item:
            return
        evidence = item.setdefault("evidence", {})
        evidence["static_analysis_clean"] = clean
        evidence["static_analysis_details"] = details
        self._save_state()

    def set_hash(self, item_id: str, expected: str, current: str):
        """Record hash verification for a module."""
        item = self._state["items"].get(item_id)
        if not item:
            return
        evidence = item.setdefault("evidence", {})
        evidence["hash_expected"] = expected
        evidence["hash_current"] = current
        evidence["hash_verified"] = (expected == current)
        self._save_state()

    # ── Check ──────────────────────────────────────────────────

    def check(self, item_id: str) -> CheckResult:
        """Check an item's approval status and whether it's ready to advance.
        
        This is the main query method both gate change-control and metacog
        module approval call into.
        """
        if self.is_exempt(item_id):
            return CheckResult(
                item_id=item_id,
                stage="approved",
                ready=True,
                reason="Exempt item — auto-approved",
                evidence=Evidence(),
            )

        item_data = self._state["items"].get(item_id)
        if not item_data:
            return CheckResult(
                item_id=item_id,
                stage="unknown",
                ready=False,
                reason=f"Item '{item_id}' not found in approval pipeline. Submit it first.",
                evidence=Evidence(),
            )

        ec_data = item_data.get("evidence_config", {})
        ec = EvidenceConfig(
            min_monitoring_hours=ec_data.get("min_monitoring_hours", DEFAULT_MIN_MONITORING_HOURS),
            min_trigger_events=ec_data.get("min_trigger_events", DEFAULT_MIN_TRIGGER_EVENTS),
            probation_hours=ec_data.get("probation_hours", DEFAULT_PROBATION_HOURS),
            max_block_rate=ec_data.get("max_block_rate", DEFAULT_MAX_PROBATION_BLOCK_RATE),
            require_clean_static=ec_data.get("require_clean_static", False),
            require_hash_match=ec_data.get("require_hash_match", False),
        )

        # Collect current evidence
        evidence = self.collect_audit_evidence(item_id)

        # Merge in stored evidence (module runs, static analysis, hash)
        stored = item_data.get("evidence", {})
        evidence.monitoring_runs = stored.get("monitoring_runs", 0)
        evidence.static_analysis_clean = stored.get("static_analysis_clean")
        evidence.hash_verified = stored.get("hash_verified")
        evidence.hash_expected = stored.get("hash_expected")
        evidence.hash_current = stored.get("hash_current")

        stage = item_data.get("stage", "submitted")

        if stage == "approved":
            return CheckResult(
                item_id=item_id,
                stage="approved",
                ready=True,
                reason="Already approved",
                evidence=evidence,
            )

        if stage == "suspended":
            return CheckResult(
                item_id=item_id,
                stage="suspended",
                ready=False,
                reason=f"Suspended: {item_data.get('suspend_reason', 'unknown')}",
                evidence=evidence,
            )

        if stage == "submitted":
            return CheckResult(
                item_id=item_id,
                stage="submitted",
                ready=True,
                reason="Ready to start monitoring",
                evidence=evidence,
                next_stage="monitoring",
            )

        # Stage: monitoring or pending-approval — check evidence
        blockers = []

        # Check event count
        if evidence.event_count < ec.min_trigger_events:
            blockers.append(
                f"Only {evidence.event_count}/{ec.min_trigger_events} audit events recorded"
            )

        # Check monitoring duration
        if evidence.monitoring_hours < ec.min_monitoring_hours:
            remaining = ec.min_monitoring_hours - evidence.monitoring_hours
            blockers.append(
                f"Monitoring period: {evidence.monitoring_hours:.1f}h/{ec.min_monitoring_hours}h "
                f"({remaining:.1f}h remaining)"
            )

        # Check static analysis (for modules)
        if ec.require_clean_static and evidence.static_analysis_clean is False:
            blockers.append("Static analysis flagged suspicious patterns")

        # Check hash (for modules)
        if ec.require_hash_match and evidence.hash_verified is False:
            blockers.append(
                f"Hash mismatch: expected {evidence.hash_expected}, "
                f"got {evidence.hash_current}"
            )

        if blockers:
            # Not ready — auto-advance to monitoring if still submitted
            if stage == "submitted":
                item_data["stage"] = "monitoring"
                item_data["monitoring_started"] = datetime.now(timezone.utc).isoformat()
                self._save_state()

            return CheckResult(
                item_id=item_id,
                stage="monitoring",
                ready=False,
                reason="Monitoring — not yet ready. " + "; ".join(blockers),
                evidence=evidence,
                next_stage="pending-approval",
            )

        # All evidence requirements met
        if stage == "monitoring":
            item_data["stage"] = "pending-approval"
            self._audit("ready", item_id, "all evidence requirements met")
            self._save_state()

        return CheckResult(
            item_id=item_id,
            stage="pending-approval",
            ready=True,
            reason=(
                f"Ready for approval: {evidence.event_count} events over "
                f"{evidence.monitoring_hours:.1f}h"
            ),
            evidence=evidence,
            next_stage="approved",
        )

    # ── Approve / Suspend ──────────────────────────────────────

    def approve(self, item_id: str, approved_by: str = "human") -> CheckResult:
        """Approve an item. Requires check() to show ready=True first."""
        result = self.check(item_id)
        
        if result.stage == "approved":
            return result

        if not result.ready and result.stage not in ("pending-approval",):
            return CheckResult(
                item_id=item_id,
                stage=result.stage,
                ready=False,
                reason=f"Cannot approve: {result.reason}",
                evidence=result.evidence,
            )

        item_data = self._state["items"].get(item_id)
        if not item_data:
            return result

        now = datetime.now(timezone.utc).isoformat()
        item_data["stage"] = "approved"
        item_data["approved_at"] = now
        item_data["approved_by"] = approved_by
        self._audit("approved", item_id, f"by={approved_by}")
        self._save_state()

        return CheckResult(
            item_id=item_id,
            stage="approved",
            ready=True,
            reason=f"Approved by {approved_by}",
            evidence=result.evidence,
        )

    def suspend(self, item_id: str, reason: str = "manual") -> CheckResult:
        """Suspend an approved or monitoring item."""
        item_data = self._state["items"].get(item_id)
        if not item_data:
            return CheckResult(
                item_id=item_id,
                stage="unknown",
                ready=False,
                reason="Item not found",
                evidence=Evidence(),
            )

        now = datetime.now(timezone.utc).isoformat()
        item_data["stage"] = "suspended"
        item_data["suspended_at"] = now
        item_data["suspend_reason"] = reason
        self._audit("suspended", item_id, reason)
        self._save_state()

        return CheckResult(
            item_id=item_id,
            stage="suspended",
            ready=False,
            reason=f"Suspended: {reason}",
            evidence=Evidence(),
        )

    def resubmit(self, item_id: str) -> CheckResult:
        """Re-submit a suspended item (restarts monitoring)."""
        item_data = self._state["items"].get(item_id)
        if not item_data:
            return CheckResult(
                item_id=item_id,
                stage="unknown",
                ready=False,
                reason="Item not found",
                evidence=Evidence(),
            )

        now = datetime.now(timezone.utc).isoformat()
        item_data["stage"] = "monitoring"
        item_data["monitoring_started"] = now
        item_data["suspended_at"] = None
        item_data["suspend_reason"] = None
        item_data["approved_at"] = None
        item_data["approved_by"] = None
        # Reset evidence
        item_data["evidence"] = {}
        self._audit("resubmitted", item_id, "monitoring restarted")
        self._save_state()

        return self.check(item_id)

    # ── Query ──────────────────────────────────────────────────

    def list_items(self, kind: Optional[str] = None, stage: Optional[str] = None) -> list:
        """List items, optionally filtered by kind and/or stage."""
        results = []
        for item_id, item_data in self._state["items"].items():
            if kind and item_data.get("kind") != kind:
                continue
            if stage and item_data.get("stage") != stage:
                continue
            results.append(self._dict_to_item(item_data))
        return results

    def get_dashboard(self) -> dict:
        """Generate a dashboard summary of all items."""
        items = self._state.get("items", {})
        by_stage = {}
        by_kind = {}
        for item_id, item_data in items.items():
            stage = item_data.get("stage", "unknown")
            kind = item_data.get("kind", "unknown")
            by_stage.setdefault(stage, []).append(item_id)
            by_kind.setdefault(kind, []).append(item_id)

        return {
            "total": len(items),
            "by_stage": {k: len(v) for k, v in by_stage.items()},
            "by_kind": {k: len(v) for k, v in by_kind.items()},
            "items_by_stage": by_stage,
            "exempt_count": len(self.exempt),
            "last_updated": self._state.get("last_updated"),
        }

    # ── Helpers ────────────────────────────────────────────────

    def _dict_to_item(self, d: dict) -> ApprovalItem:
        """Convert dict to ApprovalItem."""
        return ApprovalItem(
            item_id=d.get("item_id", ""),
            kind=d.get("kind", ""),
            display_name=d.get("display_name", ""),
            stage=d.get("stage", "submitted"),
            submitted_at=d.get("submitted_at"),
            monitoring_started=d.get("monitoring_started"),
            approved_at=d.get("approved_at"),
            approved_by=d.get("approved_by"),
            suspended_at=d.get("suspended_at"),
            suspend_reason=d.get("suspend_reason"),
            evidence_config=d.get("evidence_config", {}),
            evidence=d.get("evidence", {}),
            metadata=d.get("metadata", {}),
        )


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    """CLI interface for the approval pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Unified Approval Pipeline")
    sub = parser.add_subparsers(dest="command")

    # submit
    p_submit = sub.add_parser("submit", help="Submit an item for approval")
    p_submit.add_argument("item_id", help="Item ID (e.g., gate:research-gate)")
    p_submit.add_argument("--kind", required=True, help="Item kind (gate, module, config)")
    p_submit.add_argument("--name", default="", help="Display name")
    p_submit.add_argument("--min-hours", type=float, default=DEFAULT_MIN_MONITORING_HOURS)
    p_submit.add_argument("--min-events", type=int, default=DEFAULT_MIN_TRIGGER_EVENTS)

    # check
    p_check = sub.add_parser("check", help="Check item status")
    p_check.add_argument("item_id", help="Item ID")

    # approve
    p_approve = sub.add_parser("approve", help="Approve an item")
    p_approve.add_argument("item_id", help="Item ID")
    p_approve.add_argument("--by", default="human", help="Approver identity")

    # suspend
    p_suspend = sub.add_parser("suspend", help="Suspend an item")
    p_suspend.add_argument("item_id", help="Item ID")
    p_suspend.add_argument("--reason", default="manual", help="Suspension reason")

    # resubmit
    p_resub = sub.add_parser("resubmit", help="Re-submit a suspended item")
    p_resub.add_argument("item_id", help="Item ID")

    # list
    p_list = sub.add_parser("list", help="List all items")
    p_list.add_argument("--kind", help="Filter by kind")
    p_list.add_argument("--stage", help="Filter by stage")

    # dashboard
    sub.add_parser("dashboard", help="Show pipeline dashboard")

    # sync-gates
    sub.add_parser("sync-gates", help="Sync current gate config into pipeline")

    args = parser.parse_args()
    pipeline = ApprovalPipeline()

    if args.command == "submit":
        ec = EvidenceConfig(
            min_monitoring_hours=args.min_hours,
            min_trigger_events=args.min_events,
        )
        item = pipeline.submit(args.item_id, kind=args.kind, display_name=args.name, evidence_config=ec)
        print(f"✅ Submitted: {item.item_id} → stage={item.stage}")

    elif args.command == "check":
        result = pipeline.check(args.item_id)
        icon = {"approved": "✅", "monitoring": "👁️", "pending-approval": "⏳",
                "suspended": "🚨", "unknown": "❓"}.get(result.stage, "?")
        print(f"{icon} {result.item_id}: {result.stage}")
        print(f"   Ready: {result.ready}")
        print(f"   Reason: {result.reason}")
        if result.evidence.event_count > 0:
            print(f"   Events: {result.evidence.event_count}")
            print(f"   Monitoring: {result.evidence.monitoring_hours:.1f}h")

    elif args.command == "approve":
        result = pipeline.approve(args.item_id, approved_by=args.by)
        if result.stage == "approved":
            print(f"✅ Approved: {result.item_id}")
        else:
            print(f"❌ Cannot approve: {result.reason}")

    elif args.command == "suspend":
        result = pipeline.suspend(args.item_id, reason=args.reason)
        print(f"🚨 Suspended: {result.item_id} — {args.reason}")

    elif args.command == "resubmit":
        result = pipeline.resubmit(args.item_id)
        print(f"🔄 Resubmitted: {result.item_id} → {result.stage}")

    elif args.command == "list":
        items = pipeline.list_items(kind=args.kind, stage=args.stage)
        if not items:
            print("No items found.")
            return
        print(f"{'ID':<45} {'Kind':<10} {'Stage':<20}")
        print("-" * 80)
        for item in items:
            icon = {"approved": "✅", "monitoring": "👁️", "pending-approval": "⏳",
                    "suspended": "🚨"}.get(item.stage, "?")
            print(f"{item.item_id:<45} {item.kind:<10} {icon} {item.stage}")

    elif args.command == "dashboard":
        dash = pipeline.get_dashboard()
        print("# Approval Pipeline Dashboard\n")
        print(f"Total items: {dash['total']}")
        print(f"Exempt: {dash['exempt_count']}")
        print(f"\nBy stage:")
        for stage, count in sorted(dash["by_stage"].items()):
            icon = {"approved": "✅", "monitoring": "👁️", "pending-approval": "⏳",
                    "suspended": "🚨"}.get(stage, "?")
            print(f"  {icon} {stage}: {count}")
        print(f"\nBy kind:")
        for kind, count in sorted(dash["by_kind"].items()):
            print(f"  {kind}: {count}")
        if dash.get("last_updated"):
            print(f"\nLast updated: {dash['last_updated'][:19]}")

    elif args.command == "sync-gates":
        _sync_gates(pipeline)

    else:
        parser.print_help()


def _sync_gates(pipeline: ApprovalPipeline):
    """Sync current gate configuration into the pipeline.
    
    Reads openclaw.json and submits all enabled gates as pipeline items.
    """
    openclaw_json = Path.home() / ".openclaw" / "openclaw.json"
    if not openclaw_json.exists():
        print("❌ openclaw.json not found")
        return

    with open(openclaw_json) as f:
        cfg = json.load(f)

    oc_gates = (cfg.get("plugins", {}).get("entries", {})
                .get("openclaw-gates", {}).get("config", {}))

    # Named gates
    named_gates = {
        "researchGate": "research-gate",
        "todoGate": "todo-gate",
        "changeControl": "change-control",
        "configSafety": "config-safety",
        "threadFidelity": "thread-fidelity",
    }

    synced = 0
    for config_key, gate_name in named_gates.items():
        gate_cfg = oc_gates.get(config_key, {})
        if not gate_cfg.get("enabled"):
            continue
        item_id = f"gate:{gate_name}"
        mode = gate_cfg.get("mode", "enforce")
        pipeline.submit(
            item_id,
            kind="gate",
            display_name=f"{gate_name} ({mode})",
            metadata={"current_mode": mode, "config_key": config_key},
        )
        synced += 1
        print(f"  📋 {item_id} (mode={mode})")

    # Static rules
    rules = oc_gates.get("rules", {})
    for rule_name, rule_cfg in rules.items():
        if not rule_cfg.get("enabled"):
            continue
        item_id = f"gate:{rule_name}"
        mode = rule_cfg.get("mode", "enforce")
        pipeline.submit(
            item_id,
            kind="gate",
            display_name=f"{rule_name} ({mode})",
            metadata={"current_mode": mode, "rule_name": rule_name},
        )
        synced += 1
        print(f"  📋 {item_id} (mode={mode})")

    print(f"\n✅ Synced {synced} gates into approval pipeline")


if __name__ == "__main__":
    main()
