# Unified Approval Pipeline

Single approval system for gates, metacog modules, and future consumers.

## Problem

Two separate approval systems existed:

1. **Gate change-control** (`openclaw-gates/change-control.ts`) — blocks `log→enforce` promotions without evidence
2. **Metacog module approval** (`discovery.py`) — `discover→monitor→approve` pipeline for modules

Both shared the same concepts (monitoring period, evidence thresholds, audit trail) but implemented them independently.

## Solution

`pipeline.py` provides a single `ApprovalPipeline` class that both systems call into:

```
submitted → monitoring → pending-approval → approved → (suspended)
```

### For Gates (TypeScript consumer)
The gate `change-control.ts` calls `pipeline.py check gate:<name>` via subprocess before allowing mode promotions.

### For Metacog Modules (Python consumer)  
The `discovery.py` module calls `ApprovalPipeline` directly via Python import.

### Shared Features
- Same monitoring period (configurable per-item, default 24h)
- Same evidence thresholds (default: 20 events + 24h monitoring)
- Same audit trail format (JSON in `~/.openclaw/state/approval-pipeline.json`)
- Same exempt list (foundational safety rules like `bias-to-action`)
- Future: same MFA requirement when MFA gate is built

## CLI Usage

```bash
# Submit items
python3 pipeline.py submit gate:research-gate --kind gate
python3 pipeline.py submit module:openclaw-gates/gate-health --kind module

# Check status
python3 pipeline.py check gate:research-gate

# Approve after monitoring
python3 pipeline.py approve gate:research-gate

# Suspend
python3 pipeline.py suspend module:some-module --reason "hash mismatch"

# Dashboard
python3 pipeline.py dashboard

# Sync all gates from openclaw.json
python3 pipeline.py sync-gates

# List by kind or stage
python3 pipeline.py list --kind gate
python3 pipeline.py list --stage monitoring
```

## Integration Points

### Gate change-control.ts
Calls `python3 pipeline.py check gate:<name>` and parses JSON exit code:
- Exit 0 + `"ready": true` → allow promotion
- Exit 0 + `"ready": false` → block with reason

### Metacog discovery.py
Imports `ApprovalPipeline` and delegates approval tracking:
```python
from approval_pipeline.pipeline import ApprovalPipeline
pipeline = ApprovalPipeline()
pipeline.submit(f"module:{module_id}", kind="module", ...)
result = pipeline.check(f"module:{module_id}")
```

## State

All state lives in `~/.openclaw/state/approval-pipeline.json` — single source of truth.

## Architecture

```
┌─────────────────────────┐     ┌─────────────────────────┐
│  Gate change-control.ts │     │  Metacog discovery.py   │
│  (TypeScript plugin)    │     │  (Python skill)         │
└────────────┬────────────┘     └────────────┬────────────┘
             │ subprocess                     │ import
             │ check/approve                  │ check/approve
             ▼                                ▼
        ┌─────────────────────────────────────────┐
        │         Approval Pipeline               │
        │         (pipeline.py)                    │
        │                                         │
        │  submit → monitoring → pending → approve│
        │                                         │
        │  State: ~/.openclaw/state/              │
        │         approval-pipeline.json          │
        │                                         │
        │  Audit: in-state trail (last 500)       │
        │  Evidence: audit log files              │
        └─────────────────────────────────────────┘
```
