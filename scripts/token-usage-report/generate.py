#!/usr/bin/env python3
"""
Token Usage Report Generator for OpenClaw
Parses session data to produce an HTML report of token usage over a configurable window.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

CDT = timezone(timedelta(hours=-5))
OPENCLAW_DIR = Path.home() / ".openclaw"
AGENTS_DIR = OPENCLAW_DIR / "agents"


def load_sessions(agent="main"):
    """Load sessions.json for the given agent."""
    path = AGENTS_DIR / agent / "sessions" / "sessions.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def parse_jsonl_usage(filepath, cutoff_ms):
    """Extract per-message usage from a session jsonl file."""
    hourly = {}
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    api_calls = 0

    if not os.path.exists(filepath):
        return hourly, total_input, total_output, total_cache_read, total_cache_write, api_calls

    with open(filepath) as f:
        for line in f:
            try:
                rec = json.loads(line)
                msg = rec.get("message", {})
                usage = msg.get("usage", {})
                if not usage:
                    continue

                inp = usage.get("input", 0) or 0
                out = usage.get("output", 0) or 0
                cr = usage.get("cacheRead", 0) or 0
                cw = usage.get("cacheWrite", 0) or 0
                total_input += inp
                total_output += out
                total_cache_read += cr
                total_cache_write += cw
                api_calls += 1

                # Parse timestamp
                ts = msg.get("timestamp", rec.get("timestamp"))
                dt = None
                if isinstance(ts, (int, float)) and ts > 1e12:
                    dt = datetime.fromtimestamp(ts / 1000, tz=CDT)
                elif isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(CDT)

                if dt and dt.timestamp() * 1000 >= cutoff_ms:
                    hk = dt.strftime("%Y-%m-%d %H:00")
                    if hk not in hourly:
                        hourly[hk] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "calls": 0}
                    hourly[hk]["input"] += inp
                    hourly[hk]["output"] += out
                    hourly[hk]["cache_read"] += cr
                    hourly[hk]["cache_write"] += cw
                    hourly[hk]["calls"] += 1
            except Exception:
                pass

    return hourly, total_input, total_output, total_cache_read, total_cache_write, api_calls


def gather_data(hours=48, agents=None):
    """Gather usage data across all agents."""
    if agents is None:
        agents = ["main", "isolated"]

    now = datetime.now(CDT)
    cutoff = now - timedelta(hours=hours)
    cutoff_ms = int(cutoff.timestamp() * 1000)

    all_sessions = []
    global_hourly = {}

    for agent in agents:
        sessions = load_sessions(agent)
        for k, v in sessions.items():
            updated = v.get("updatedAt", 0)
            started = v.get("startedAt", 0)
            if updated < cutoff_ms and started < cutoff_ms:
                continue

            sf = v.get("sessionFile", "")
            hourly, inp, out, cr, cw, calls = parse_jsonl_usage(sf, cutoff_ms)

            sess = {
                "id": v.get("sessionId", ""),
                "agent": agent,
                "started": started,
                "updated": updated,
                "cost": v.get("estimatedCostUsd", 0) or 0,
                "model": v.get("model", "unknown"),
                "channel": v.get("lastChannel", "unknown") or "unknown",
                "contextTokens": v.get("contextTokens", 0),
                "compactions": v.get("compactionCount", 0) or 0,
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read": cr,
                "cache_write": cw,
                "api_calls": calls,
                "hourly": hourly,
            }
            all_sessions.append(sess)

            for hk, data in hourly.items():
                if hk not in global_hourly:
                    global_hourly[hk] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "calls": 0, "sessions": 0}
                global_hourly[hk]["input"] += data["input"]
                global_hourly[hk]["output"] += data["output"]
                global_hourly[hk]["cache_read"] += data["cache_read"]
                global_hourly[hk]["cache_write"] += data["cache_write"]
                global_hourly[hk]["calls"] += data["calls"]
                global_hourly[hk]["sessions"] += 1

    # Also build hourly cost from sessions.json estimatedCostUsd (for sessions with no jsonl usage)
    hourly_cost = {}
    for s in all_sessions:
        ts = s["started"] or s["updated"]
        dt = datetime.fromtimestamp(ts / 1000, tz=CDT)
        hk = dt.strftime("%Y-%m-%d %H:00")
        if hk not in hourly_cost:
            hourly_cost[hk] = {"cost": 0, "sessions": 0}
        hourly_cost[hk]["cost"] += s["cost"]
        hourly_cost[hk]["sessions"] += 1

    # Merge hourly sources
    all_hours = sorted(set(list(global_hourly.keys()) + list(hourly_cost.keys())))
    merged_hourly = []
    for h in all_hours:
        row = {
            "hour": h,
            "input": global_hourly.get(h, {}).get("input", 0),
            "output": global_hourly.get(h, {}).get("output", 0),
            "cache_read": global_hourly.get(h, {}).get("cache_read", 0),
            "calls": global_hourly.get(h, {}).get("calls", 0),
            "sessions": hourly_cost.get(h, {}).get("sessions", 0),
            "cost": hourly_cost.get(h, {}).get("cost", 0),
        }
        merged_hourly.append(row)

    # By-model breakdown
    by_model = {}
    for s in all_sessions:
        m = s["model"]
        if m not in by_model:
            by_model[m] = {"sessions": 0, "cost": 0, "input": 0, "output": 0}
        by_model[m]["sessions"] += 1
        by_model[m]["cost"] += s["cost"]
        by_model[m]["input"] += s["input_tokens"]
        by_model[m]["output"] += s["output_tokens"]

    # By-channel breakdown
    by_channel = {}
    for s in all_sessions:
        c = s["channel"]
        if c not in by_channel:
            by_channel[c] = {"sessions": 0, "cost": 0, "input": 0, "output": 0}
        by_channel[c]["sessions"] += 1
        by_channel[c]["cost"] += s["cost"]
        by_channel[c]["input"] += s["input_tokens"]
        by_channel[c]["output"] += s["output_tokens"]

    return {
        "generated": now.isoformat(),
        "window_hours": hours,
        "cutoff": cutoff.isoformat(),
        "total_sessions": len(all_sessions),
        "total_cost": sum(s["cost"] for s in all_sessions),
        "total_input": sum(s["input_tokens"] for s in all_sessions),
        "total_output": sum(s["output_tokens"] for s in all_sessions),
        "total_cache_read": sum(s["cache_read"] for s in all_sessions),
        "hourly": merged_hourly,
        "by_model": by_model,
        "by_channel": by_channel,
        "top_sessions": sorted(all_sessions, key=lambda x: x["cost"], reverse=True)[:25],
    }


def fmt_num(n):
    """Format large numbers with commas."""
    return f"{n:,.0f}"


def fmt_cost(c):
    """Format cost in USD."""
    if c >= 1:
        return f"${c:,.2f}"
    elif c >= 0.01:
        return f"${c:.4f}"
    else:
        return f"${c:.6f}"


def generate_html(data, output_path):
    """Generate the HTML report."""
    hourly = data["hourly"]
    max_input = max((h["input"] for h in hourly), default=1) or 1
    max_cost = max((h["cost"] for h in hourly), default=1) or 1

    # Build hourly rows
    hourly_rows = ""
    for h in hourly:
        input_pct = (h["input"] / max_input) * 100 if max_input else 0
        cost_pct = (h["cost"] / max_cost) * 100 if max_cost else 0
        hourly_rows += f"""
        <tr>
            <td class="hour">{h["hour"]}</td>
            <td class="num">{fmt_num(h["input"])}</td>
            <td class="num">{fmt_num(h["output"])}</td>
            <td class="num">{fmt_num(h["cache_read"])}</td>
            <td class="num">{h["calls"]}</td>
            <td class="num">{h["sessions"]}</td>
            <td class="num cost">{fmt_cost(h["cost"])}</td>
            <td class="bar-cell">
                <div class="bar input-bar" style="width:{input_pct:.1f}%"></div>
            </td>
        </tr>"""

    # Top sessions rows
    top_rows = ""
    for s in data["top_sessions"]:
        started = datetime.fromtimestamp(s["started"] / 1000, tz=CDT).strftime("%m/%d %H:%M") if s["started"] else "N/A"
        top_rows += f"""
        <tr>
            <td class="mono">{s["id"][:12]}…</td>
            <td>{started}</td>
            <td>{s["model"]}</td>
            <td>{s["channel"]}</td>
            <td class="num">{fmt_num(s["input_tokens"])}</td>
            <td class="num">{fmt_num(s["output_tokens"])}</td>
            <td class="num cost">{fmt_cost(s["cost"])}</td>
            <td class="num">{s["compactions"]}</td>
        </tr>"""

    # Model breakdown rows
    model_rows = ""
    for m, d in sorted(data["by_model"].items(), key=lambda x: x[1]["cost"], reverse=True):
        model_rows += f"""
        <tr>
            <td>{m}</td>
            <td class="num">{d["sessions"]}</td>
            <td class="num">{fmt_num(d["input"])}</td>
            <td class="num">{fmt_num(d["output"])}</td>
            <td class="num cost">{fmt_cost(d["cost"])}</td>
        </tr>"""

    # Channel breakdown rows
    channel_rows = ""
    for c, d in sorted(data["by_channel"].items(), key=lambda x: x[1]["cost"], reverse=True):
        channel_rows += f"""
        <tr>
            <td>{c}</td>
            <td class="num">{d["sessions"]}</td>
            <td class="num">{fmt_num(d["input"])}</td>
            <td class="num">{fmt_num(d["output"])}</td>
            <td class="num cost">{fmt_cost(d["cost"])}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw Token Usage Report</title>
<style>
  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --orange: #d29922;
    --purple: #bc8cff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.5;
  }}
  h1 {{ color: var(--accent); margin-bottom: 4px; font-size: 1.8em; }}
  h2 {{ color: var(--text); margin: 32px 0 12px; font-size: 1.3em; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  .meta {{ color: var(--muted); font-size: 0.9em; margin-bottom: 24px; }}
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }}
  .card .label {{ color: var(--muted); font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }}
  .card .value {{ font-size: 1.8em; font-weight: 700; margin-top: 4px; }}
  .card .value.cost {{ color: var(--red); }}
  .card .value.tokens {{ color: var(--green); }}
  .card .value.sessions {{ color: var(--accent); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--surface);
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 24px;
    font-size: 0.9em;
  }}
  th {{
    background: var(--border);
    color: var(--text);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}
  th.num, td.num {{ text-align: right; }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}
  tr:hover {{ background: rgba(88,166,255,0.05); }}
  .mono {{ font-family: 'SF Mono', 'Cascadia Code', monospace; font-size: 0.85em; }}
  .hour {{ font-family: 'SF Mono', 'Cascadia Code', monospace; }}
  .cost {{ color: var(--orange); font-weight: 600; }}
  .bar-cell {{ width: 200px; padding: 8px 12px; }}
  .bar {{
    height: 14px;
    border-radius: 3px;
    min-width: 2px;
    transition: width 0.3s;
  }}
  .input-bar {{ background: linear-gradient(90deg, var(--accent), var(--purple)); }}
  .warn {{ background: rgba(248,81,73,0.15); border-left: 3px solid var(--red); padding: 12px 16px; border-radius: 4px; margin: 16px 0; }}
  .warn strong {{ color: var(--red); }}
  footer {{ color: var(--muted); font-size: 0.8em; margin-top: 40px; text-align: center; }}
</style>
</head>
<body>
<h1>🌴 OpenClaw Token Usage Report</h1>
<p class="meta">
  Generated: {data["generated"]}<br>
  Window: {data["window_hours"]}h (since {data["cutoff"]})
</p>

<div class="cards">
  <div class="card">
    <div class="label">Total Sessions</div>
    <div class="value sessions">{data["total_sessions"]}</div>
  </div>
  <div class="card">
    <div class="label">Estimated Cost</div>
    <div class="value cost">{fmt_cost(data["total_cost"])}</div>
  </div>
  <div class="card">
    <div class="label">Input Tokens</div>
    <div class="value tokens">{fmt_num(data["total_input"])}</div>
  </div>
  <div class="card">
    <div class="label">Output Tokens</div>
    <div class="value tokens">{fmt_num(data["total_output"])}</div>
  </div>
  <div class="card">
    <div class="label">Cache Read Tokens</div>
    <div class="value" style="color:var(--purple)">{fmt_num(data["total_cache_read"])}</div>
  </div>
  <div class="card">
    <div class="label">Avg Cost/Session</div>
    <div class="value cost">{fmt_cost(data["total_cost"] / max(data["total_sessions"], 1))}</div>
  </div>
</div>

{"<div class='warn'><strong>⚠️ High-cost session detected.</strong> Session " + data["top_sessions"][0]["id"][:12] + "… accounts for " + fmt_cost(data["top_sessions"][0]["cost"]) + " (" + f'{data["top_sessions"][0]["cost"]/max(data["total_cost"],1)*100:.0f}' + "% of total). " + str(data["top_sessions"][0]["compactions"]) + " compactions suggest runaway context accumulation.</div>" if data["top_sessions"] and data["top_sessions"][0]["cost"] > data["total_cost"] * 0.5 else ""}

<h2>📊 Hourly Breakdown</h2>
<table>
  <thead>
    <tr>
      <th>Hour (CDT)</th>
      <th class="num">Input Tokens</th>
      <th class="num">Output Tokens</th>
      <th class="num">Cache Read</th>
      <th class="num">API Calls</th>
      <th class="num">Sessions</th>
      <th class="num">Est. Cost</th>
      <th>Input Volume</th>
    </tr>
  </thead>
  <tbody>
    {hourly_rows}
  </tbody>
</table>

<h2>🏆 Top Sessions by Cost</h2>
<table>
  <thead>
    <tr>
      <th>Session ID</th>
      <th>Started</th>
      <th>Model</th>
      <th>Channel</th>
      <th class="num">Input Tokens</th>
      <th class="num">Output Tokens</th>
      <th class="num">Est. Cost</th>
      <th class="num">Compactions</th>
    </tr>
  </thead>
  <tbody>
    {top_rows}
  </tbody>
</table>

<h2>🤖 By Model</h2>
<table>
  <thead>
    <tr>
      <th>Model</th>
      <th class="num">Sessions</th>
      <th class="num">Input Tokens</th>
      <th class="num">Output Tokens</th>
      <th class="num">Est. Cost</th>
    </tr>
  </thead>
  <tbody>
    {model_rows}
  </tbody>
</table>

<h2>📡 By Channel</h2>
<table>
  <thead>
    <tr>
      <th>Channel</th>
      <th class="num">Sessions</th>
      <th class="num">Input Tokens</th>
      <th class="num">Output Tokens</th>
      <th class="num">Est. Cost</th>
    </tr>
  </thead>
  <tbody>
    {channel_rows}
  </tbody>
</table>

<footer>
  Generated by OpenClaw Token Usage Report skill &middot; Data from sessions.json + session transcripts
</footer>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate OpenClaw token usage report")
    parser.add_argument("--hours", type=int, default=48, help="Window in hours (default: 48)")
    parser.add_argument("--output", type=str, default=None, help="Output HTML path")
    parser.add_argument("--json", action="store_true", help="Also output raw JSON")
    parser.add_argument("--agents", type=str, default="main,isolated", help="Comma-separated agent names")
    args = parser.parse_args()

    agents = [a.strip() for a in args.agents.split(",")]
    data = gather_data(hours=args.hours, agents=agents)

    output = args.output or f"/tmp/openclaw-token-usage-{args.hours}h.html"
    generate_html(data, output)
    print(f"Report: {output}")
    print(f"Sessions: {data['total_sessions']} | Cost: {fmt_cost(data['total_cost'])} | Input: {fmt_num(data['total_input'])} | Output: {fmt_num(data['total_output'])}")

    if args.json:
        json_path = output.replace(".html", ".json")
        # Remove hourly from top_sessions to keep json clean
        export = {k: v for k, v in data.items() if k != "top_sessions"}
        export["top_sessions"] = [{k2: v2 for k2, v2 in s.items() if k2 != "hourly"} for s in data["top_sessions"]]
        with open(json_path, "w") as f:
            json.dump(export, f, indent=2)
        print(f"JSON:   {json_path}")


if __name__ == "__main__":
    main()
