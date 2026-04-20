#!/usr/bin/env python3
"""IMSVA CDT Analyzer — parse an extracted CDT bundle and produce a structured JSON report.

Usage:
    python3 parse_cdt.py <cdt_root> [--output report.json] [--format json|markdown]

<cdt_root> must be the top-level extracted CDT directory containing:
    ReadmeFirst.txt, SystemInfo.Report.txt, IMSVA/LogFile/{Event1..Event5}

Outputs a structured analysis covering:
    1. CDT metadata & system snapshot
    2. Scanner identity & cluster info
    3. Postfix config assessment (timeouts, content_filter)
    4. Deferral classification by failure mode (A/B/C)
    5. Incident detection (mass deferrals, service restarts, chronic patterns)
    6. Cross-correlation: maillog ↔ log.imss ↔ imssps timestamps
    7. Config risk flags
    8. Recommendations
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_files(root: str, pattern: str) -> list[str]:
    """Glob for files under root matching pattern, sorted."""
    return sorted(glob.glob(os.path.join(root, pattern)))


def safe_read(path: str, encoding: str = "utf-8") -> str:
    """Read file, return empty string on failure."""
    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        return ""


def grep_lines(text: str, pattern: str, flags: int = re.IGNORECASE) -> list[str]:
    """Return all lines matching regex pattern."""
    rx = re.compile(pattern, flags)
    return [line for line in text.splitlines() if rx.search(line)]


def count_pattern(text: str, pattern: str, flags: int = re.IGNORECASE) -> int:
    return len(grep_lines(text, pattern, flags))


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_system_info(cdt_root: str) -> dict:
    """Parse SystemInfo.Report.txt for host snapshot."""
    text = safe_read(os.path.join(cdt_root, "SystemInfo.Report.txt"))
    info = {"raw_available": bool(text)}
    if not text:
        return info

    # Hostname
    m = re.search(r"^(\S+)\s+", text)
    # Try uname -n
    for line in text.splitlines():
        if "uname" in line.lower() or re.match(r"^Linux\s+\S+", line):
            parts = line.split()
            if len(parts) >= 2:
                info["hostname"] = parts[1]
                break

    # Uptime
    for line in text.splitlines():
        if "load average" in line:
            info["uptime_line"] = line.strip()
            m = re.search(r"load average:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)", line)
            if m:
                info["load_avg"] = [float(m.group(i)) for i in range(1, 4)]
            break

    # Memory
    for line in text.splitlines():
        if line.strip().startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 4:
                info["mem_total_kb"] = int(parts[1]) if parts[1].isdigit() else parts[1]
                info["mem_used_kb"] = int(parts[2]) if parts[2].isdigit() else parts[2]
                info["mem_free_kb"] = int(parts[3]) if parts[3].isdigit() else parts[3]
            break

    # Disk - look for df output
    df_lines = []
    in_df = False
    for line in text.splitlines():
        if re.match(r"^Filesystem\s+", line):
            in_df = True
            continue
        if in_df:
            if line.strip() == "" or line.startswith("="):
                in_df = False
                continue
            df_lines.append(line.strip())
    if df_lines:
        info["disk_usage"] = df_lines[:10]  # Top 10

    # IP addresses
    ips = re.findall(r"inet addr:([\d.]+)", text)
    if ips:
        info["ip_addresses"] = ips

    # eth0 MAC
    m = re.search(r"HWaddr\s+([\da-fA-F:]+)", text)
    if m:
        info["mac_address"] = m.group(1)

    return info


def parse_scanner_identity(cdt_root: str) -> dict:
    """Extract scanner_id, uuid, and key settings from imss.ini."""
    ini_path = os.path.join(cdt_root, "IMSVA", "LogFile", "Event1", "imss.ini")
    text = safe_read(ini_path)
    identity = {}

    for key in ("scanner_id", "uuid"):
        m = re.search(rf"^{key}\s*=\s*(.+)$", text, re.MULTILINE)
        if m:
            identity[key] = m.group(1).strip()

    # Worker pool settings
    for key in ("proc_min_init_num", "proc_max_worker_proc", "proc_max_connections"):
        m = re.search(rf"^{key}\s*=\s*(\d+)", text, re.MULTILINE)
        if m:
            identity[key] = int(m.group(1))

    return identity


def parse_postfix_config(cdt_root: str) -> dict:
    """Parse main.cf and master.cf for key settings."""
    event5 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event5")
    main_cf = safe_read(os.path.join(event5, "main.cf"))
    master_cf = safe_read(os.path.join(event5, "master.cf"))

    config = {"risks": []}

    # content_filter
    m = re.search(r"^content_filter\s*=\s*(.+)$", main_cf, re.MULTILINE)
    if m:
        config["content_filter"] = m.group(1).strip()

    # imss_timeout
    m = re.search(r"^imss_timeout\s*=\s*(.+)$", main_cf, re.MULTILINE)
    if m:
        config["imss_timeout"] = m.group(1).strip()

    # imss_connect_timeout
    m = re.search(r"^imss_connect_timeout\s*=\s*(.+)$", main_cf, re.MULTILINE)
    if m:
        val = m.group(1).strip()
        config["imss_connect_timeout"] = val
        # Risk flag: ≤2s is dangerously tight
        secs = _parse_time_to_secs(val)
        if secs is not None and secs <= 2:
            config["risks"].append({
                "setting": "imss_connect_timeout",
                "value": val,
                "risk": "HIGH",
                "detail": f"Connect timeout of {val} causes chronic deferrals when imssd workers are momentarily slow to accept. Recommend ≥5s.",
            })

    # smtp_helo_timeout
    m = re.search(r"^smtp_helo_timeout\s*=\s*(.+)$", main_cf, re.MULTILINE)
    if m:
        config["smtp_helo_timeout"] = m.group(1).strip()

    # imss transport in master.cf
    if "imss" in master_cf:
        config["imss_transport_present"] = True
        m = re.search(r"^imss\s+unix\s+.*?(\d+)\s+smtp", master_cf, re.MULTILINE)
        if m:
            config["imss_transport_maxproc"] = int(m.group(1))

    return config


def _parse_time_to_secs(val: str) -> float | None:
    """Parse Postfix time value (e.g. '1s', '10m', '2h') to seconds."""
    m = re.match(r"^(\d+)\s*(s|m|h|d)?$", val.strip(), re.IGNORECASE)
    if not m:
        return None
    n = int(m.group(1))
    unit = (m.group(2) or "s").lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return n * multipliers.get(unit, 1)


def parse_policy_server_config(cdt_root: str) -> dict:
    """Extract imssps thread pool and timeout settings from imssps logs and imss.ini."""
    event3 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event3")
    ps_config = {"risks": []}

    # Try imssps logs first (startup messages contain Read setting lines)
    for path in find_files(event3, "imssps.*"):
        # Read only first 2000 lines — startup config is near the top
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                head = "".join(f.readline() for _ in range(2000))
        except (FileNotFoundError, PermissionError):
            continue

        for key in ("threads", "max_threads", "poolSize", "maxSize", "idleSize",
                     "recv_timeout_secs", "send_timeout_secs"):
            m = re.search(rf"Read setting '{key}'.*?value is '(\d+)'", head)
            if m and key not in ps_config:
                ps_config[key] = int(m.group(1))

        # Only need the first file with startup config
        if ps_config.get("threads"):
            break

    # Also check imss.ini [policy_server] section for timeout settings
    ini_path = os.path.join(cdt_root, "IMSVA", "LogFile", "Event1", "imss.ini")
    ini_text = safe_read(ini_path)
    if ini_text:
        for key in ("recv_timeout_secs", "send_timeout_secs"):
            if key not in ps_config:
                m = re.search(rf"^{key}\s*=\s*(\d+)", ini_text, re.MULTILINE)
                if m:
                    ps_config[key] = int(m.group(1))

    # Risk flags
    threads = ps_config.get("threads", 0)
    if 0 < threads < 50:
        ps_config["risks"].append({
            "setting": "imssps threads",
            "value": threads,
            "risk": "MEDIUM",
            "detail": f"Policy Server thread pool of {threads} may be undersized for bulk recipient fan-out. Serial per-recipient LDAP lookups on a single thread mean pool size mainly affects concurrent message capacity, not per-message speed.",
        })

    return ps_config


# ---------------------------------------------------------------------------
# Deferral classification
# ---------------------------------------------------------------------------

# Failure mode patterns (from TM-03926071 analysis)
DEFERRAL_PATTERNS = {
    "A_connect_timeout": re.compile(
        r"connect to (?:localhost|127\.0\.0\.1)\[127\.0\.0\.1\]:10025.*Connection timed out",
        re.IGNORECASE
    ),
    "A_connect_refused": re.compile(
        r"connect to (?:localhost|127\.0\.0\.1)\[127\.0\.0\.1\]:10025.*Connection refused",
        re.IGNORECASE
    ),
    "B_data_timeout": re.compile(
        r"conversation with (?:localhost|127\.0\.0\.1)\[127\.0\.0\.1\]:10025 timed out",
        re.IGNORECASE
    ),
    "C_451_scan_uncertain": re.compile(
        r"said:\s*451.*Scan result uncertain", re.IGNORECASE
    ),
    "C_451_start_ruleset": re.compile(
        r"said:\s*451.*StartRuleSetRetrieval", re.IGNORECASE
    ),
    "C_451_other": re.compile(
        r"said:\s*4[0-9]{2}\s", re.IGNORECASE
    ),
    "lost_connection": re.compile(
        r"lost connection with (?:localhost|127\.0\.0\.1).*initial server greeting",
        re.IGNORECASE
    ),
}


def classify_deferrals(cdt_root: str) -> dict:
    """Classify all status=deferred lines from maillog files."""
    event5 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event5")
    maillog_files = find_files(event5, "maillog*")

    results = {
        "total_deferrals": 0,
        "by_mode": Counter(),
        "by_hour": defaultdict(int),
        "by_queue_id": Counter(),
        "sample_lines": [],
        "mass_deferral_queue_ids": [],  # queue IDs with ≥100 deferrals
    }

    for mlog in maillog_files:
        try:
            fh = open(mlog, "r", encoding="utf-8", errors="replace")
        except (FileNotFoundError, PermissionError):
            continue
        for line in fh:
            if "status=deferred" not in line:
                continue

            results["total_deferrals"] += 1

            # Extract queue ID
            qid_match = re.search(r"([A-F0-9]{8,12}):", line)
            if qid_match:
                results["by_queue_id"][qid_match.group(1)] += 1

            # Extract hour
            ts_match = re.match(r"(\w+\s+\d+\s+\d+:\d+)", line)
            if ts_match:
                results["by_hour"][ts_match.group(1)[:ts_match.group(1).rfind(":")]] += 1

            # Classify failure mode
            classified = False
            for mode, pattern in DEFERRAL_PATTERNS.items():
                if mode == "C_451_other":
                    continue  # Check this last as fallback
                if pattern.search(line):
                    results["by_mode"][mode] += 1
                    classified = True
                    break

            if not classified:
                if DEFERRAL_PATTERNS["C_451_other"].search(line):
                    results["by_mode"]["C_451_other"] += 1
                else:
                    results["by_mode"]["unclassified"] += 1

            # Keep first 5 sample lines per mode
            if len(results["sample_lines"]) < 20:
                results["sample_lines"].append(line.strip()[:300])

    # Identify mass deferral queue IDs (≥100 deferrals on same QID)
    for qid, count in results["by_queue_id"].most_common():
        if count >= 100:
            results["mass_deferral_queue_ids"].append({"queue_id": qid, "count": count})

    # Convert counters for JSON
    results["by_mode"] = dict(results["by_mode"])
    results["by_hour"] = dict(sorted(results["by_hour"].items()))
    results["by_queue_id"] = dict(results["by_queue_id"].most_common(20))

    return results


# ---------------------------------------------------------------------------
# Incident detection
# ---------------------------------------------------------------------------

def detect_service_restarts(cdt_root: str) -> list[dict]:
    """Detect IMSS service start/stop events from sysevt logs."""
    event3 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event3")
    restarts = []

    for path in find_files(event3, "sysevt.imss.*"):
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except (FileNotFoundError, PermissionError):
            continue
        for line in fh:
            # Event 20001 = IMSS Daemon starts, 20002 = IMSS Daemon stopped
            if re.search(r"(20001|20002)", line):
                ts_match = re.match(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", line)
                event_type = "start" if "20001" in line else "stop"
                restarts.append({
                    "timestamp": ts_match.group(1) if ts_match else "unknown",
                    "event": event_type,
                    "line": line.strip()[:200],
                })

    return restarts


def detect_scanner_errors(cdt_root: str) -> dict:
    """Scan log.imss files for error patterns."""
    event3 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event3")
    errors = {
        "policy_server_failures": [],
        "scan_uncertain": [],
        "soap_faults": [],
        "core_dumps": [],
        "total_errors": 0,
    }

    # log.imss errors — stream line-by-line to avoid loading entire file
    for path in find_files(event3, "log.imss.*"):
        fname = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "[ERROR]" not in line and "[FATAL]" not in line:
                        continue
                    errors["total_errors"] += 1

                    if len(errors["policy_server_failures"]) < 20 and (
                        "Failed to receive policy response" in line or "RetrieveRuleSet" in line
                    ):
                        ts = _extract_timestamp(line)
                        errors["policy_server_failures"].append({
                            "timestamp": ts,
                            "file": fname,
                            "line": line.strip()[:200],
                        })
                    elif len(errors["scan_uncertain"]) < 20 and "Scan result uncertain" in line:
                        ts = _extract_timestamp(line)
                        errors["scan_uncertain"].append({
                            "timestamp": ts,
                            "file": fname,
                            "line": line.strip()[:200],
                        })
        except (FileNotFoundError, PermissionError):
            continue

    # imssps SOAP faults — stream line-by-line
    for path in find_files(event3, "imssps.*"):
        fname = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "SOAP FAULT" not in line and "Failed to return policy request" not in line:
                        continue
                    ts = _extract_timestamp(line)
                    errors["soap_faults"].append({
                        "timestamp": ts,
                        "file": fname,
                        "line": line.strip()[:200],
                    })
                    if len(errors["soap_faults"]) >= 20:
                        break
        except (FileNotFoundError, PermissionError):
            continue

    # Core dumps
    ts_core_path = os.path.join(cdt_root, "IMSVA", "LogFile", "Event4", "timestamp_core.txt")
    text = safe_read(ts_core_path)
    if text.strip():
        errors["core_dumps"] = [l.strip() for l in text.splitlines() if l.strip()]

    # Trim lists to prevent huge output
    for key in ("policy_server_failures", "scan_uncertain", "soap_faults"):
        if len(errors[key]) > 20:
            errors[key] = errors[key][:20]
            errors[f"{key}_truncated"] = True

    return errors


def _extract_timestamp(line: str) -> str:
    """Extract timestamp from IMSVA log line."""
    m = re.match(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", line)
    return m.group(1) if m else "unknown"


def detect_mass_recipient_messages(cdt_root: str) -> list[dict]:
    """Find messages with high recipient counts (nrcpt≥50) from maillog."""
    event5 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event5")
    bulk_msgs = []

    for path in find_files(event5, "maillog*"):
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except (FileNotFoundError, PermissionError):
            continue
        for line in fh:
            m = re.search(r"([A-F0-9]{8,12}):.*nrcpt=(\d+)", line)
            if m:
                nrcpt = int(m.group(2))
                if nrcpt >= 50:
                    qid = m.group(1)
                    sender_m = re.search(r"from=<([^>]*)>", line)
                    sender = sender_m.group(1) if sender_m else "unknown"
                    bulk_msgs.append({
                        "queue_id": qid,
                        "nrcpt": nrcpt,
                        "sender": sender,
                        "line": line.strip()[:300],
                    })

    return bulk_msgs


def check_tls_issues(cdt_root: str) -> dict:
    """Check tlsagent logs for TLS delivery failures."""
    event3 = os.path.join(cdt_root, "IMSVA", "LogFile", "Event3")
    tls = {"failures": [], "forced_domains_count": 0}

    # Count forced TLS domains
    forced_path = os.path.join(cdt_root, "IMSVA", "LogFile", "Event1", "fox_tls_forced_domain.list")
    text = safe_read(forced_path)
    if text:
        tls["forced_domains_count"] = len([l for l in text.splitlines() if l.strip() and not l.startswith("#")])

    # TLS agent errors
    for path in find_files(event3, "tlsagent.*"):
        text = safe_read(path)
        for line in text.splitlines():
            if re.search(r"(error|fail|reject|refused)", line, re.IGNORECASE):
                tls["failures"].append(line.strip()[:200])
                if len(tls["failures"]) >= 10:
                    break
        if len(tls["failures"]) >= 10:
            break

    return tls


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_recommendations(analysis: dict) -> list[dict]:
    """Generate ranked recommendations from analysis results."""
    recs = []

    # R1: imss_connect_timeout
    postfix = analysis.get("postfix_config", {})
    if postfix.get("imss_connect_timeout"):
        secs = _parse_time_to_secs(postfix["imss_connect_timeout"])
        if secs is not None and secs <= 2:
            mode_a = analysis.get("deferrals", {}).get("by_mode", {})
            a_count = mode_a.get("A_connect_timeout", 0) + mode_a.get("A_connect_refused", 0)
            recs.append({
                "id": "R1",
                "priority": "IMMEDIATE",
                "risk": "LOW",
                "title": f"Raise imss_connect_timeout from {postfix['imss_connect_timeout']} to 5s-10s",
                "detail": f"Current {postfix['imss_connect_timeout']} timeout causes {a_count} Mode A deferrals in this CDT window. Raising to 5-10s eliminates chronic background deferrals with no realistic downside.",
                "setting": "main.cf: imss_connect_timeout",
                "current": postfix["imss_connect_timeout"],
                "recommended": "5s",
            })

    # R2: Mass deferral detection → policy server tuning
    mass = analysis.get("deferrals", {}).get("mass_deferral_queue_ids", [])
    if mass:
        recs.append({
            "id": "R2",
            "priority": "HIGH",
            "risk": "MEDIUM",
            "title": "Tune policy server timeouts for bulk recipient messages",
            "detail": f"Detected {len(mass)} queue ID(s) with ≥100 deferrals (mass fan-out). imssps processes recipients SERIALLY per SOAP request. For large DLs, raise recv_timeout_secs (currently {analysis.get('policy_server', {}).get('recv_timeout_secs', 'unknown')}s) to allow cold-cache LDAP lookups to complete.",
            "setting": "imss.ini: [policy_server] recv_timeout_secs, send_timeout_secs",
            "current": f"recv={analysis.get('policy_server', {}).get('recv_timeout_secs', '?')}s, send={analysis.get('policy_server', {}).get('send_timeout_secs', '?')}s",
            "recommended": "recv_timeout_secs=180, send_timeout_secs=60",
        })

    # R3: Service restart investigation
    restarts = analysis.get("service_restarts", [])
    if restarts:
        recs.append({
            "id": "R3",
            "priority": "MEDIUM",
            "risk": "LOW",
            "title": "Investigate service restart triggers",
            "detail": f"Detected {len(restarts)} service start/stop events. Correlate with admin console audit log to determine if planned or watchdog-initiated.",
        })

    # R4: Core dumps
    cores = analysis.get("scanner_errors", {}).get("core_dumps", [])
    if cores:
        recs.append({
            "id": "R4",
            "priority": "HIGH",
            "risk": "LOW",
            "title": "Investigate core dumps",
            "detail": f"Found {len(cores)} core dump timestamp(s) in Event4/timestamp_core.txt. imssd worker crashes directly cause deferrals.",
        })

    return recs


def build_report(cdt_root: str) -> dict:
    """Build complete analysis report for a CDT."""
    cdt_root = os.path.abspath(cdt_root)
    report = {
        "cdt_path": cdt_root,
        "cdt_name": os.path.basename(cdt_root),
        "analysis_timestamp": datetime.now().isoformat(),
    }

    # Parse components
    report["system_info"] = parse_system_info(cdt_root)
    report["scanner_identity"] = parse_scanner_identity(cdt_root)
    report["postfix_config"] = parse_postfix_config(cdt_root)
    report["policy_server"] = parse_policy_server_config(cdt_root)
    report["deferrals"] = classify_deferrals(cdt_root)
    report["service_restarts"] = detect_service_restarts(cdt_root)
    report["scanner_errors"] = detect_scanner_errors(cdt_root)
    report["bulk_messages"] = detect_mass_recipient_messages(cdt_root)
    report["tls_issues"] = check_tls_issues(cdt_root)

    # Aggregate config risks
    report["config_risks"] = (
        report["postfix_config"].pop("risks", []) +
        report["policy_server"].pop("risks", [])
    )

    # Generate recommendations
    report["recommendations"] = generate_recommendations(report)

    # Summary
    deferrals = report["deferrals"]
    report["summary"] = {
        "scanner_id": report["scanner_identity"].get("scanner_id", "unknown"),
        "hostname": report["system_info"].get("hostname", "unknown"),
        "total_deferrals": deferrals["total_deferrals"],
        "dominant_failure_mode": max(deferrals["by_mode"], key=deferrals["by_mode"].get) if deferrals["by_mode"] else "none",
        "mass_deferral_incidents": len(deferrals["mass_deferral_queue_ids"]),
        "service_restart_events": len(report["service_restarts"]),
        "scanner_errors_total": report["scanner_errors"]["total_errors"],
        "config_risks_count": len(report["config_risks"]),
        "recommendations_count": len(report["recommendations"]),
    }

    return report


def report_to_markdown(report: dict) -> str:
    """Convert JSON report to readable markdown."""
    lines = []
    s = report.get("summary", {})

    lines.append(f"# CDT Analysis — {report.get('cdt_name', 'Unknown')}")
    lines.append("")
    lines.append(f"**Scanner**: {s.get('scanner_id', '?')} ({s.get('hostname', '?')})")
    lines.append(f"**Analyzed**: {report.get('analysis_timestamp', '?')}")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total deferrals**: {s.get('total_deferrals', 0)}")
    lines.append(f"- **Dominant failure mode**: {s.get('dominant_failure_mode', 'none')}")
    lines.append(f"- **Mass deferral incidents**: {s.get('mass_deferral_incidents', 0)}")
    lines.append(f"- **Service restart events**: {s.get('service_restart_events', 0)}")
    lines.append(f"- **Scanner errors**: {s.get('scanner_errors_total', 0)}")
    lines.append(f"- **Config risk flags**: {s.get('config_risks_count', 0)}")
    lines.append("")

    # Deferral breakdown
    lines.append("## Deferral Classification")
    lines.append("")
    deferrals = report.get("deferrals", {})
    for mode, count in sorted(deferrals.get("by_mode", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- **{mode}**: {count}")
    lines.append("")

    # Mass deferrals
    mass = deferrals.get("mass_deferral_queue_ids", [])
    if mass:
        lines.append("### Mass Deferral Queue IDs (≥100 deferrals)")
        lines.append("")
        for item in mass:
            lines.append(f"- `{item['queue_id']}`: {item['count']} deferrals")
        lines.append("")

    # Bulk messages
    bulk = report.get("bulk_messages", [])
    if bulk:
        lines.append("## Bulk Recipient Messages (≥50 recipients)")
        lines.append("")
        for msg in bulk:
            lines.append(f"- `{msg['queue_id']}`: {msg['nrcpt']} recipients, from `{msg['sender']}`")
        lines.append("")

    # Config risks
    risks = report.get("config_risks", [])
    if risks:
        lines.append("## Configuration Risk Flags")
        lines.append("")
        for risk in risks:
            lines.append(f"### ⚠️ {risk['setting']} = `{risk['value']}` [{risk['risk']}]")
            lines.append(f"{risk['detail']}")
            lines.append("")

    # Scanner errors
    errors = report.get("scanner_errors", {})
    if errors.get("policy_server_failures"):
        lines.append("## Policy Server Failures (log.imss)")
        lines.append("")
        for err in errors["policy_server_failures"][:5]:
            lines.append(f"- `{err['timestamp']}` ({err['file']}): {err['line'][:120]}")
        lines.append("")

    if errors.get("soap_faults"):
        lines.append("## SOAP Faults (imssps)")
        lines.append("")
        for err in errors["soap_faults"][:5]:
            lines.append(f"- `{err['timestamp']}` ({err['file']}): {err['line'][:120]}")
        lines.append("")

    if errors.get("core_dumps"):
        lines.append("## ⚠️ Core Dumps Detected")
        lines.append("")
        for dump in errors["core_dumps"]:
            lines.append(f"- {dump}")
        lines.append("")

    # Service restarts
    restarts = report.get("service_restarts", [])
    if restarts:
        lines.append("## Service Restart Events")
        lines.append("")
        for r in restarts:
            lines.append(f"- `{r['timestamp']}` — {r['event']}: {r['line'][:120]}")
        lines.append("")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        lines.append("## Recommendations")
        lines.append("")
        for rec in recs:
            lines.append(f"### {rec['id']}: {rec['title']} [{rec['priority']}, risk: {rec['risk']}]")
            lines.append(f"{rec['detail']}")
            if rec.get("current"):
                lines.append(f"- Current: `{rec['current']}`")
            if rec.get("recommended"):
                lines.append(f"- Recommended: `{rec['recommended']}`")
            lines.append("")

    # Postfix config
    pf = report.get("postfix_config", {})
    lines.append("## Postfix Configuration")
    lines.append("")
    for k, v in pf.items():
        if k != "risks":
            lines.append(f"- `{k}`: `{v}`")
    lines.append("")

    # Policy server config
    ps = report.get("policy_server", {})
    if ps:
        lines.append("## Policy Server Configuration")
        lines.append("")
        for k, v in ps.items():
            if k != "risks":
                lines.append(f"- `{k}`: `{v}`")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IMSVA CDT Analyzer")
    parser.add_argument("cdt_root", help="Path to extracted CDT directory")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="json",
                        help="Output format (default: json)")
    args = parser.parse_args()

    if not os.path.isdir(args.cdt_root):
        print(f"Error: {args.cdt_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    report = build_report(args.cdt_root)

    if args.format == "markdown":
        output = report_to_markdown(report)
    else:
        output = json.dumps(report, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
