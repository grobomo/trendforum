#!/usr/bin/env python3
"""Module: trello-bridge — Create Trello cards from metacognition findings.

Scans the daily metacognition log for actionable findings and creates cards
on the Coconut Todo list so the trello-work cron (Opus) picks them up.

Deduplication: checks existing Coconut Todo cards by name prefix to avoid
creating duplicates for already-tracked findings.

Tier: quick (runs after other modules, bridges findings → action)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
METACOG_DIR = WORKSPACE / "memory" / "metacognition"
TRELLO_API = WORKSPACE / "scripts" / "trello-api.py"
COCONUT_TODO_LIST = "6954d3af836b51597afff8e9"
BRIDGE_STATE_FILE = METACOG_DIR / "trello-bridge-state.json"

# Findings that match these patterns are actionable (worth a card)
ACTIONABLE_PATTERNS = [
    (r"🔴", "critical"),      # Critical issues
    (r"NEW REGRESSION", "regression"),
    (r"Repeated error \((\d+)x\)", "repeated_error"),
    (r"Duplicate lesson", "cleanup"),
    (r"OVERDUE commitment", "commitment"),
    (r"missing sections", "cleanup"),
    (r"hook status is 'new'", "hook_review"),
    (r"Unresolved CR:", "conflict"),
]

# Skip these — noise or already tracked elsewhere
SKIP_PATTERNS = [
    r"Teams",           # Teams monitoring suspended
    r"HEARTBEAT_OK",
    r"Self-Audit",      # Self-audit is informational
    r"ℹ️.*unverified",  # Info-level, not actionable
]


def load_state() -> dict:
    """Load bridge state (tracks what's already been created)."""
    if BRIDGE_STATE_FILE.exists():
        return json.loads(BRIDGE_STATE_FILE.read_text())
    return {"created_findings": [], "last_processed_line": 0}


def save_state(state: dict):
    """Save bridge state."""
    BRIDGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BRIDGE_STATE_FILE.write_text(json.dumps(state, indent=2))


def get_existing_cards() -> list[str]:
    """Get names of existing cards in Coconut Todo list."""
    try:
        result = subprocess.run(
            ["python3", str(TRELLO_API), "list-cards", "--list", COCONUT_TODO_LIST],
            capture_output=True, text=True, check=True, timeout=30
        )
        cards = json.loads(result.stdout)
        return [c["name"] for c in cards]
    except Exception as e:
        print(f"Warning: couldn't fetch existing cards: {e}", file=sys.stderr)
        return []


def create_card(name: str, desc: str) -> bool:
    """Create a Trello card on Coconut Todo list."""
    try:
        result = subprocess.run(
            ["python3", str(TRELLO_API), "create-card",
             "--list", COCONUT_TODO_LIST,
             "--name", name,
             "--desc", desc],
            capture_output=True, text=True, check=True, timeout=30
        )
        card = json.loads(result.stdout)
        print(f"Created card: {card.get('id', '?')} — {name}")
        return True
    except Exception as e:
        print(f"Error creating card '{name}': {e}", file=sys.stderr)
        return False


def extract_actionable_findings(log_path: Path, since_line: int = 0) -> list[dict]:
    """Parse metacog daily log and extract actionable findings."""
    if not log_path.exists():
        return []

    lines = log_path.read_text().splitlines()
    findings = []
    current_section = ""
    current_time = ""

    for i, line in enumerate(lines):
        if i < since_line:
            continue

        # Track section headers
        section_match = re.match(r"^## (\d{2}:\d{2}).*— (.+)", line)
        if section_match:
            current_time = section_match.group(1)
            current_section = section_match.group(2).strip()
            continue

        # Skip non-finding lines
        if not line.startswith("- "):
            continue

        # Check skip patterns first
        skip = False
        for sp in SKIP_PATTERNS:
            if re.search(sp, line):
                skip = True
                break
        if skip:
            continue

        # Check actionable patterns
        for pattern, category in ACTIONABLE_PATTERNS:
            match = re.search(pattern, line)
            if match:
                findings.append({
                    "line_num": i,
                    "category": category,
                    "section": current_section,
                    "time": current_time,
                    "text": line.lstrip("- ").strip(),
                    "severity": "critical" if category in ("critical", "regression") else "normal",
                })
                break

    return findings


def sanitize_credentials(text: str) -> str:
    """Strip any credentials, API keys, or tokens from text before writing to Trello."""
    text = re.sub(r'(?:TRELLO_KEY|key)\s*[=:]\s*["\']?[a-f0-9]{32}["\']?', '[CREDENTIAL_REDACTED]', text)
    text = re.sub(r'(?:TRELLO_TOKEN|token)\s*[=:]\s*["\']?ATTA[a-fA-F0-9]{40,}["\']?', '[CREDENTIAL_REDACTED]', text)
    text = re.sub(r'(?:API_KEY|SECRET|PASSWORD|APIKEY)\s*[=:]\s*["\'][^"\']+["\']', '[CREDENTIAL_REDACTED]', text)
    text = re.sub(r'key=[a-f0-9]{16,}', 'key=***', text)
    text = re.sub(r'token=[a-zA-Z0-9]{16,}', 'token=***', text)
    return text


def finding_to_card_name(finding: dict) -> str:
    """Generate a Trello card name from a finding."""
    prefix = "[metacog]"
    text = sanitize_credentials(finding["text"])

    # Shorten common patterns
    if finding["category"] == "repeated_error":
        match = re.search(r"Repeated error \((\d+)x\): (.{0,60})", text)
        if match:
            return f"{prefix} Fix repeated error ({match.group(1)}x): {match.group(2)}..."

    if finding["category"] == "regression":
        return f"{prefix} Fix regression: {text[:80]}"

    if finding["category"] == "critical":
        return f"{prefix} 🔴 {text[:80]}"

    if finding["category"] == "cleanup":
        return f"{prefix} Cleanup: {text[:80]}"

    if finding["category"] == "commitment":
        return f"{prefix} Overdue: {text[:80]}"

    if finding["category"] == "conflict":
        return f"{prefix} Resolve: {text[:80]}"

    if finding["category"] == "hook_review":
        return f"{prefix} Review: {text[:80]}"

    return f"{prefix} {text[:80]}"


def finding_to_card_desc(finding: dict) -> str:
    """Generate card description from finding."""
    safe_text = sanitize_credentials(finding["text"])
    return (
        f"**Source:** Metacognition {finding['section']} ({finding['time']} CT)\n"
        f"**Category:** {finding['category']}\n"
        f"**Severity:** {finding['severity']}\n\n"
        f"**Finding:**\n{safe_text}\n\n"
        f"---\n*Auto-created by metacog trello-bridge on {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    )


def is_duplicate(card_name: str, existing_cards: list[str], state: dict) -> bool:
    """Check if a finding already has a card (fuzzy match on key terms)."""
    # Exact match
    if card_name in existing_cards:
        return True

    # Check state for previously created findings
    if card_name in state.get("created_findings", []):
        return True

    # Fuzzy: strip prefix and check if core text matches any existing card
    core = card_name.replace("[metacog]", "").strip()
    for existing in existing_cards:
        existing_core = existing.replace("[metacog]", "").strip()
        # If >70% of words overlap, consider it a duplicate
        core_words = set(core.lower().split())
        existing_words = set(existing_core.lower().split())
        if core_words and existing_words:
            overlap = len(core_words & existing_words) / max(len(core_words), 1)
            if overlap > 0.7:
                return True

    return False


def run(output_dir: Path) -> int:
    """Run the trello-bridge module. Return 0=ok, 1=findings, 2=error."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = METACOG_DIR / f"{today}.md"

    state = load_state()

    # Reset line counter if it's a new day
    if state.get("date") != today:
        state["last_processed_line"] = 0
        state["date"] = today
        state["created_findings"] = [
            f for f in state.get("created_findings", [])
            if len(state.get("created_findings", [])) < 50  # Keep last 50
        ]

    findings = extract_actionable_findings(log_path, state["last_processed_line"])

    if not findings:
        print("No new actionable findings.")
        save_state(state)
        return 0

    print(f"Found {len(findings)} actionable finding(s).")

    # Get existing cards for dedup
    existing_cards = get_existing_cards()

    created = 0
    skipped = 0

    for finding in findings:
        card_name = finding_to_card_name(finding)

        if is_duplicate(card_name, existing_cards, state):
            print(f"  Skip (duplicate): {card_name}")
            skipped += 1
            continue

        card_desc = finding_to_card_desc(finding)
        if create_card(card_name, card_desc):
            created += 1
            state["created_findings"].append(card_name)
            existing_cards.append(card_name)  # Avoid dupes within same run

    # Update processed line
    if findings:
        state["last_processed_line"] = max(f["line_num"] for f in findings)

    save_state(state)

    # Log to daily metacog output
    log_entry = (
        f"\n## {datetime.now().strftime('%H:%M')} — Trello Bridge\n"
        f"- Scanned {len(findings)} finding(s): {created} cards created, {skipped} skipped (duplicate)\n"
    )
    if created > 0:
        for finding in findings:
            card_name = finding_to_card_name(finding)
            if card_name in state["created_findings"][-created:]:
                log_entry += f"- → Created: {card_name}\n"

    with open(output_dir / f"{today}.md", "a") as f:
        f.write(log_entry)

    print(f"\nDone: {created} created, {skipped} skipped")
    return 1 if created > 0 else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        default=METACOG_DIR,
    )
    args = parser.parse_args()
    sys.exit(run(args.output_dir))
