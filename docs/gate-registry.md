# Gate Registry

What every gate does, why it exists, and where it is in the lifecycle.

## How Gate Lifecycle Works

Every gate progresses through four phases. Three require Joel's explicit approval (MFA) to advance.

```
New → Log-only → Enforcing → Trusted
       🔑 MFA      🔑 MFA      🔑 MFA
```

| Phase | What it does | What it means |
|-------|-------------|---------------|
| **New** | Exists in code, not active | Written but Joel hasn't approved activation |
| **Log-only** | Records what it *would* block, blocks nothing | Safe to observe — shows impact without risk |
| **Enforcing** | Actually blocks + we're watching for false positives | Actively protecting but still proving itself |
| **Trusted** | Blocks, no longer actively monitored | Proven through its watch period with clean results |

**Why three MFA gates?** I shouldn't be able to write a gate, activate it, and trust it without Joel reviewing the impact at each stage. Each approval is a checkpoint: "does this gate do what we intended, without breaking things we need?"

**Watch period:** After promotion to Enforcing, each gate has a watch window (default 72h, configurable per-gate). During this window the metacog cron monitors block rate. If blocks exceed 15% of events, it alerts. After the watch period passes clean, the gate is eligible for Trusted — but still needs Joel's MFA to graduate.

---

## Active Gates

### 📝 Log-only

#### Research Gate
- **What:** Blocks spec/design writes unless a timestamped research doc exists
- **Why:** Joel's standing order — research before building. Prevents me from jumping to code without checking what exists first
- **How:** Phase 1 checks file existence + freshness. Phase 2 calls Sonnet to validate research quality and alignment with user vision
- **Config:** `openclaw-gates.config.researchGate`
- **Monitoring since:** 2026-04-25

#### Todo Gate
- **What:** Blocks work unless an active task is tracked in todo.md
- **Why:** Prevents untracked work — everything should be visible in the task system
- **Config:** `openclaw-gates.config.todoGate`
- **Monitoring since:** 2026-04-25

#### Change Control Gate
- **What:** Blocks config changes that flip a gate to enforce without sufficient audit evidence
- **Why:** Prevents premature gate promotion — this is the gate that guards the other gates
- **How:** Intercepts writes to openclaw.json, checks audit logs for the target gate's event count and monitoring duration
- **Config:** `openclaw-gates.config.changeControl`
- **Monitoring since:** 2026-04-25

#### Config Safety
- **What:** Creates timestamped backups of ~/.openclaw files before any write/edit
- **Why:** Insurance policy — any config change can be rolled back from the backup
- **Config:** `openclaw-gates.config.configSafety`
- **Monitoring since:** 2026-04-22

### 🔒 Enforcing

#### Bias to Action (static rule)
- **What:** Blocks outbound messages that ask permission instead of acting
- **Why:** Joel's standing order — act first, don't ask "should I do X?"
- **Watch period:** 72h (started 2026-04-25)
- **Config:** `openclaw-gates.config.rules.bias-to-action`
- **Note:** "Born enforce" — foundational behavior rule, exempt from change-control gate

#### Archive Before Delete (static rule)
- **What:** Blocks rm/delete/unlink commands, requires archive instead
- **Why:** Joel's rule — never delete, always archive. Recoverable beats gone
- **Watch period:** 72h (started 2026-04-25)
- **Config:** `openclaw-gates.config.rules.archive-before-delete`
- **Note:** "Born enforce" — foundational safety rule, exempt from change-control gate

### 🛡️ Trusted

_(None yet — no gates have completed their watch period + received MFA approval)_

---

## Metacog Modules

These run on the self-audit cron and monitor system health.

| Module | Tier | What it does |
|--------|------|-------------|
| session-analyzer | quick (15m) | Counts tool calls, detects anti-patterns (polling addiction, token hemorrhage) |
| change-control | quick (15m) | Reports gate deployment posture, flags enforce-without-evidence |
| gate-lifecycle | quick (15m) | Full lifecycle dashboard, post-enforce monitoring, block rate tracking |
| decision-check | quick (15m) | Checks DECISIONS.md for contradictions or stale decisions |
| conflict-resolution | deep (1h) | Detects conflicts between lessons, specs, and hooks |
| lesson-review | deep (1h) | Reviews Lessons board, checks for new lessons, applies resolved ones |
| pattern-detector | deep (1h) | Detects circular rebuilds, repeated failures, token waste |

---

## Audit Logs

| Log | Source | What it captures |
|-----|--------|-----------------|
| `~/.openclaw/logs/audit-logger.jsonl` | claude-code-gates | Every tool call in Claude Code workers (pre + post), module results, timing |
| `~/.openclaw/logs/openclaw-gates-audit.jsonl` | openclaw-gates | Gate decisions (todo, research, change-control, config-safety, inner-voice) |

Both are JSONL, greppable, auto-rotate at 10MB.

---

_Last updated: 2026-04-26_
