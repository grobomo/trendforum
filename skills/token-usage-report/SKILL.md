# Token Usage Report

Generate an HTML report of OpenClaw token usage over a configurable time window.

## When to Use

- User asks about token usage, cost, or burn rate
- Investigating high-cost sessions or runaway token consumption
- Periodic cost audits
- "How much did we spend?" / "What's burning tokens?"

## How to Run

```bash
python3 ~/.openclaw/workspace/scripts/token-usage-report/generate.py --hours <N> [--output <path>] [--json] [--agents main,isolated]
```

### Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--hours` | 48 | Lookback window in hours |
| `--output` | `/tmp/openclaw-token-usage-<N>h.html` | Output HTML path |
| `--json` | off | Also emit a raw JSON data file |
| `--agents` | `main,isolated` | Comma-separated agent names to scan |

### Examples

```bash
# Last 48 hours (default)
python3 ~/.openclaw/workspace/scripts/token-usage-report/generate.py

# Last 24 hours with JSON export
python3 ~/.openclaw/workspace/scripts/token-usage-report/generate.py --hours 24 --json

# Last 7 days, custom output
python3 ~/.openclaw/workspace/scripts/token-usage-report/generate.py --hours 168 --output /tmp/weekly-usage.html
```

## Data Sources

- **sessions.json**: `~/.openclaw/agents/<agent>/sessions/sessions.json` — session metadata including `estimatedCostUsd`, `model`, `channel`, `compactionCount`
- **Session transcripts**: `*.jsonl` files — per-message `usage` blocks with `input`, `output`, `cacheRead`, `cacheWrite` token counts and cost breakdowns

## Report Sections

1. **Summary cards** — total sessions, cost, input/output tokens, cache reads, avg cost/session
2. **High-cost warning** — auto-flagged if one session > 50% of total cost
3. **Hourly breakdown** — tokens, API calls, sessions, cost per hour with bar chart
4. **Top sessions by cost** — session ID, start time, model, channel, tokens, compactions
5. **By model** — aggregate per model
6. **By channel** — aggregate per channel (slack, webchat, exec-event, etc.)

## OpenClaw Built-in Usage Tracking

OpenClaw tracks per-session usage natively in `sessions.json`:
- `estimatedCostUsd` — running cost estimate per session
- `contextTokens` — context window size
- `totalTokensFresh` — fresh token flag
- `compactionCount` — number of context compactions (high = runaway session)

Per-message granularity is in the `.jsonl` transcript files with `usage.input`, `usage.output`, `usage.cacheRead`, `usage.cost.total`.

There is no built-in report/dashboard — this skill fills that gap.

## Notes

- Cost estimates use the pricing embedded by the provider at call time (from `usage.cost.total` in transcripts)
- Sessions with `compactionCount > 10` are a red flag for runaway context loops
- The `unknown` channel typically means cron/heartbeat/internal sessions
- Cache read tokens are significantly cheaper than fresh input tokens
