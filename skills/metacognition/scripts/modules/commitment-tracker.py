#!/usr/bin/env python3
"""Module: commitment-tracker — Detect and track promises made in outbound messages.

Scans recent session logs and Slack message history for outbound commitment
language ("I'll", "I will", "by Xpm", "check back", "let me test", etc.)
and tracks them in a commitments file. On each run, checks for overdue
commitments and emits warnings.

Tier: quick (15-min cron)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
COMMITMENTS_FILE = WORKSPACE / "memory" / "commitments.json"

# Patterns that indicate a commitment/promise
COMMITMENT_PATTERNS = [
    # Time-bound promises
    r"(?:I'll|I will|i'll|i will|going to|gonna)\s+(?:test|check|do|build|send|post|run|follow up|report back|get back|circle back|update|fix|review|finish|complete|deliver|wire|enable)\b",
    r"check(?:ing)?\s+back\s+(?:at|by|in|around)\b",
    r"(?:by|at|around|before)\s+\d{1,2}\s*(?:am|pm|AM|PM)\b",
    r"(?:by|before)\s+(?:end of day|eod|EOD|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday)\b",
    r"(?:will|I'll)\s+(?:have|get)\s+(?:this|that|it)\s+(?:done|ready|finished|completed)\b",
    r"(?:give me|need)\s+(?:\d+\s+)?(?:minutes?|hours?|min)\b.*(?:I'll|then)\b",
    r"(?:let me|lemme)\s+(?:test|check|try|run|look|dig|investigate|build)\b.*(?:and|then)\s+(?:report|check|get) back\b",
    r"ETA[:\s]+\d",
    r"target(?:ing)?[:\s]+\d",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in COMMITMENT_PATTERNS]

# Noise filters — skip cron/automated self-talk
NOISE_PATTERNS = [
    re.compile(r"I'll run the (?:monitor|session|health|slack|metacog)", re.IGNORECASE),
    re.compile(r"I'll check (?:the last|each|for missed|each Slack)", re.IGNORECASE),
    re.compile(r"I'll (?:scan|read|load|parse|fetch|pull) (?:the|recent|this)", re.IGNORECASE),
    re.compile(r"Let me (?:check|scan|read|look at|pull|fetch)", re.IGNORECASE),
    # Internal tool narration (not human-facing commitments)
    re.compile(r"^(?:Now |Let me |I'll )(?:check|run|scan|read|look|load|parse)", re.IGNORECASE),
]

def is_noise(text: str) -> bool:
    """Filter out cron/automated self-talk that isn't a real commitment."""
    return any(p.search(text) for p in NOISE_PATTERNS)

# Patterns to extract a time deadline from commitment text
TIME_PATTERNS = [
    (re.compile(r"(?:at|by|around|before)\s+(\d{1,2})\s*(am|pm|AM|PM)", re.IGNORECASE), "time"),
    (re.compile(r"(?:by|before)\s+(end of day|eod|tonight)", re.IGNORECASE), "eod"),
    (re.compile(r"(?:by|before)\s+(tomorrow)", re.IGNORECASE), "tomorrow"),
    (re.compile(r"(?:in|give me|need)\s+(\d+)\s*(minutes?|hours?|min|hr)", re.IGNORECASE), "relative"),
]


def load_commitments() -> list:
    if COMMITMENTS_FILE.exists():
        try:
            return json.loads(COMMITMENTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_commitments(commitments: list):
    COMMITMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMITMENTS_FILE.write_text(json.dumps(commitments, indent=2, default=str))


def extract_deadline(text: str, msg_timestamp: str) -> str | None:
    """Try to extract a deadline from commitment text."""
    for pattern, kind in TIME_PATTERNS:
        m = pattern.search(text)
        if m:
            if kind == "time":
                hour = int(m.group(1))
                ampm = m.group(2).lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                if ampm == "am" and hour == 12:
                    hour = 0
                # Use message date + extracted time
                try:
                    msg_dt = datetime.fromisoformat(msg_timestamp.replace("Z", "+00:00"))
                    deadline = msg_dt.replace(hour=hour, minute=0, second=0)
                    # If deadline is before message time, it's probably next day
                    if deadline < msg_dt:
                        deadline += timedelta(days=1)
                    return deadline.isoformat()
                except (ValueError, TypeError):
                    return f"{hour}:00"
            elif kind == "eod":
                try:
                    msg_dt = datetime.fromisoformat(msg_timestamp.replace("Z", "+00:00"))
                    return msg_dt.replace(hour=23, minute=59, second=0).isoformat()
                except (ValueError, TypeError):
                    return "end of day"
            elif kind == "tomorrow":
                try:
                    msg_dt = datetime.fromisoformat(msg_timestamp.replace("Z", "+00:00"))
                    return (msg_dt + timedelta(days=1)).replace(hour=9, minute=0, second=0).isoformat()
                except (ValueError, TypeError):
                    return "tomorrow"
            elif kind == "relative":
                amount = int(m.group(1))
                unit = m.group(2).lower()
                try:
                    msg_dt = datetime.fromisoformat(msg_timestamp.replace("Z", "+00:00"))
                    if "hour" in unit or "hr" in unit:
                        return (msg_dt + timedelta(hours=amount)).isoformat()
                    else:
                        return (msg_dt + timedelta(minutes=amount)).isoformat()
                except (ValueError, TypeError):
                    return f"+{amount} {unit}"
    return None


def scan_session_for_commitments(session_path: Path, since_ts: float) -> list:
    """Scan a session log for outbound commitment language."""
    found = []
    try:
        with open(session_path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    role = d.get("message", {}).get("role", "")
                    if role != "assistant":
                        continue
                    content = d.get("message", {}).get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                text_parts.append(c.get("text", ""))
                        content = " ".join(text_parts)
                    if not isinstance(content, str) or len(content) < 10:
                        continue

                    ts = d.get("timestamp", "")

                    for pattern in COMPILED_PATTERNS:
                        m = pattern.search(content)
                        if m:
                            # Extract the sentence containing the match
                            start = max(0, m.start() - 80)
                            end = min(len(content), m.end() + 80)
                            snippet = content[start:end].strip()
                            # Skip cron/automated self-talk
                            if is_noise(snippet):
                                break
                            deadline = extract_deadline(content, ts)
                            found.append({
                                "text": snippet,
                                "timestamp": ts,
                                "deadline": deadline,
                                "session": session_path.stem,
                                "status": "open",
                                "pattern": pattern.pattern[:40],
                            })
                            break  # One commitment per message block
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return found


def check_overdue(commitments: list) -> list:
    """Check for commitments past their deadline."""
    now = datetime.now(timezone.utc)
    overdue = []
    for c in commitments:
        if c.get("status") != "open":
            continue
        deadline = c.get("deadline")
        if not deadline:
            # No deadline = check if older than 4 hours
            try:
                created = datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00"))
                if (now - created).total_seconds() > 4 * 3600:
                    overdue.append(c)
            except (ValueError, TypeError, KeyError):
                pass
            continue
        try:
            deadline_dt = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
            if now > deadline_dt:
                overdue.append(c)
        except (ValueError, TypeError):
            pass
    return overdue


def deduplicate(commitments: list) -> list:
    """Remove duplicate commitments based on text similarity."""
    seen = set()
    unique = []
    for c in commitments:
        key = (c.get("text", "")[:60], c.get("session", ""))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def main():
    parser = argparse.ArgumentParser(description="commitment-tracker metacognition module")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    since_ts = since.timestamp()

    sessions_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    commitments = load_commitments()
    existing_texts = {c.get("text", "")[:60] for c in commitments}

    # Scan recent sessions for new commitments
    new_found = []
    if sessions_dir.exists():
        for f in sorted(sessions_dir.glob("*.jsonl")):
            if os.path.getmtime(f) < since_ts:
                continue
            new_found.extend(scan_session_for_commitments(f, since_ts))

    # Add new ones (dedup against existing)
    added = 0
    for c in new_found:
        if c["text"][:60] not in existing_texts:
            commitments.append(c)
            existing_texts.add(c["text"][:60])
            added += 1

    # Prune fulfilled/old (>72h) commitments
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    commitments = [c for c in commitments if c.get("status") == "open" or c.get("timestamp", "") > cutoff]

    commitments = deduplicate(commitments)
    save_commitments(commitments)

    # Check for overdue
    overdue = check_overdue(commitments)

    output = {
        "total_tracked": len(commitments),
        "open": len([c for c in commitments if c.get("status") == "open"]),
        "new_found": added,
        "overdue": len(overdue),
        "overdue_items": [
            {
                "text": c["text"][:120],
                "deadline": c.get("deadline", "none"),
                "age_hours": round((datetime.now(timezone.utc) - datetime.fromisoformat(
                    c.get("timestamp", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")
                )).total_seconds() / 3600, 1),
            }
            for c in overdue
        ],
    }

    if args.json:
        print(json.dumps(output, indent=2, default=str))
    else:
        if overdue:
            for item in output["overdue_items"]:
                print(f"🔴 OVERDUE ({item['age_hours']}h): {item['text']}")
                if item["deadline"] != "none":
                    print(f"   Deadline: {item['deadline']}")
        elif added > 0:
            print(f"📋 {added} new commitment(s) tracked, {len(commitments)} total open")
        else:
            print(f"✅ {len(commitments)} commitment(s) tracked, none overdue")

    return 1 if overdue else 0


if __name__ == "__main__":
    sys.exit(main())
