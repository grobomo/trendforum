#!/usr/bin/env python3
"""
Lesson Extractor — Stage 2 of the metacognition pipeline.

Takes a raw mistake incident (from wiki/mistakes/tracker.md) and uses Sonnet
to extract an abstract, reusable lesson. Output goes to wiki/lessons/.

Usage:
  python3 scripts/extract-lesson.py --incident "narration-leak" --details "Inner voice text between tool calls delivered as real Slack messages. 5+ occurrences. Root cause: OpenClaw streams assistant output to channel."
  python3 scripts/extract-lesson.py --file wiki/mistakes/incident-013.md
  python3 scripts/extract-lesson.py --scan  # Process all unanalyzed incidents

Requires: RDSEC_API_KEY in environment or keyring.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
WIKI_DIR = WORKSPACE / "wiki"
LESSONS_DIR = WIKI_DIR / "lessons"
TRACKER_PATH = WIKI_DIR / "mistakes" / "tracker.md"
ANALYSIS_LOG = WIKI_DIR / "mistakes" / "analysis-log.json"

# Sonnet via RDsec
API_URL = "https://api.rdsec.trendmicro.com/prod/aiendpoint/v1/chat/completions"
MODEL = "claude-4.6-sonnet"

EXTRACTION_PROMPT = """You are analyzing a mistake made by an AI agent (Coconut) to extract reusable lessons.

Given this incident, produce a structured analysis in markdown format:

## Incident Summary
One-sentence description of what happened.

## Category
Which cognitive failure pattern this represents. Pick ONE primary category:
- **assertion-without-verification**: Claiming state/facts without checking
- **output-boundary-violation**: Content going to wrong destination or leaking
- **temporal-reasoning-failure**: Wrong dates, times, schedules
- **priority-inversion**: Working on low-priority items while high-priority waits
- **lazy-delegation**: Asking instead of acting, listing options instead of choosing
- **context-contamination**: Data/context from one scope leaking into another
- **overconfidence**: Committing to a course without acknowledging uncertainty
- **other**: (specify)

## Abstract Lesson
The reusable principle — what any agent (not just Coconut) should learn from this. Write as a universal rule, not tied to this specific incident. One paragraph max.

## Environmental Conditions
What conditions enabled this mistake? (e.g., multi-channel load, long session, cron context, specific tool behavior)

## Prevention
What would have prevented this? Be specific — name the mechanism (hook, check, process change).

## Hook Candidate
Is this preventable by a before_tool_call or message_sending hook? If yes, describe what the hook would check.

## Related Patterns
Does this connect to other known failure modes? Name them if so.

---
Respond ONLY with the markdown analysis. No preamble."""


def get_api_key():
    """Get RDSEC API key from env or keyring."""
    key = os.environ.get("RDSEC_API_KEY")
    if key:
        return key
    # Try keyring
    try:
        import keyring
        key = keyring.get_password("openclaw", "RDSEC_API_KEY")
        if key:
            return key
    except ImportError:
        pass
    # Try secret-tool
    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", "openclaw", "key", "RDSEC_API_KEY"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    print("ERROR: No RDSEC_API_KEY found in env, keyring, or secret-tool", file=sys.stderr)
    sys.exit(1)


def call_sonnet(prompt: str, incident_text: str) -> str:
    """Call Sonnet via RDsec API."""
    import urllib.request
    
    api_key = get_api_key()
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": incident_text}
        ],
        "max_tokens": 2000,
        "temperature": 0.3
    }).encode()
    
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"ERROR: Sonnet API call failed: {e}", file=sys.stderr)
        sys.exit(1)


def load_analysis_log() -> dict:
    """Load the log of which incidents have been analyzed."""
    if ANALYSIS_LOG.exists():
        return json.loads(ANALYSIS_LOG.read_text())
    return {"analyzed": {}}


def save_analysis_log(log: dict):
    """Save the analysis log."""
    ANALYSIS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_LOG.write_text(json.dumps(log, indent=2) + "\n")


def parse_tracker() -> list[dict]:
    """Parse the tracker.md table into incident dicts."""
    if not TRACKER_PATH.exists():
        return []
    
    content = TRACKER_PATH.read_text()
    incidents = []
    
    # Find the table rows (skip header + separator)
    in_table = False
    for line in content.split("\n"):
        if line.startswith("| #"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 7:
                incidents.append({
                    "id": parts[0],
                    "first_seen": parts[1],
                    "category": parts[2],
                    "description": parts[3],
                    "occurrences": parts[4],
                    "hook": parts[5],
                    "status": parts[6]
                })
        elif in_table and not line.startswith("|"):
            break
    
    return incidents


def extract_incident_details(incident_id: str, content: str) -> str:
    """Extract the detailed section for an incident from tracker.md."""
    # Look for ### #N — heading
    pattern = rf"### #{incident_id}\s*—.*?\n(.*?)(?=### #\d|---|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0).strip()
    return ""


def process_incident(incident: dict, details: str = "") -> str:
    """Send incident to Sonnet for analysis and save lesson."""
    incident_text = f"""Incident #{incident['id']}: {incident['category']}
First seen: {incident['first_seen']}
Description: {incident['description']}
Occurrences: {incident['occurrences']}
Current hook: {incident['hook']}
Status: {incident['status']}

{f"Detailed incident log:{chr(10)}{details}" if details else "No additional details available."}"""

    print(f"  Analyzing incident #{incident['id']} ({incident['category']})...")
    analysis = call_sonnet(EXTRACTION_PROMPT, incident_text)
    
    # Save to wiki/lessons/
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    lesson_file = LESSONS_DIR / f"{incident['id'].zfill(3)}-{incident['category']}.md"
    
    header = f"""# Lesson {incident['id']}: {incident['category']}

_Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M CDT')}_
_Source: Incident #{incident['id']} from mistakes/tracker.md_
_Analyzer: Sonnet (automated)_

"""
    lesson_file.write_text(header + analysis + "\n")
    print(f"  → Saved to {lesson_file.relative_to(WORKSPACE)}")
    return str(lesson_file)


def main():
    parser = argparse.ArgumentParser(description="Extract lessons from mistake incidents")
    parser.add_argument("--incident", help="Incident category name")
    parser.add_argument("--details", help="Incident details text")
    parser.add_argument("--file", help="Path to incident file")
    parser.add_argument("--scan", action="store_true", help="Process all unanalyzed incidents")
    parser.add_argument("--force", action="store_true", help="Re-analyze already-processed incidents")
    args = parser.parse_args()

    if args.scan:
        incidents = parse_tracker()
        if not incidents:
            print("No incidents found in tracker.")
            return
        
        log = load_analysis_log()
        tracker_content = TRACKER_PATH.read_text()
        processed = 0
        
        for incident in incidents:
            iid = incident["id"]
            if iid in log["analyzed"] and not args.force:
                print(f"  Skipping #{iid} (already analyzed)")
                continue
            
            details = extract_incident_details(iid, tracker_content)
            lesson_path = process_incident(incident, details)
            
            log["analyzed"][iid] = {
                "timestamp": datetime.now().isoformat(),
                "lesson_file": str(Path(lesson_path).relative_to(WORKSPACE)),
                "category": incident["category"]
            }
            processed += 1
        
        save_analysis_log(log)
        print(f"\nDone. Processed {processed} incidents, {len(incidents) - processed} skipped.")
        
        # Git commit in wiki worktree
        if processed > 0:
            try:
                subprocess.run(
                    ["git", "-C", str(WIKI_DIR), "add", "-A"],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ["git", "-C", str(WIKI_DIR), "commit", "-m",
                     f"Sonnet analysis: {processed} incident(s) extracted to lessons"],
                    capture_output=True, timeout=10
                )
                print("Committed to wiki branch.")
            except Exception as e:
                print(f"Git commit failed: {e}", file=sys.stderr)
    
    elif args.incident and args.details:
        incident = {
            "id": "manual",
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
            "category": args.incident,
            "description": args.details,
            "occurrences": "1",
            "hook": "no",
            "status": "new"
        }
        process_incident(incident, args.details)
    
    elif args.file:
        content = Path(args.file).read_text()
        incident = {
            "id": Path(args.file).stem,
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
            "category": "from-file",
            "description": content[:200],
            "occurrences": "1",
            "hook": "no",
            "status": "new"
        }
        process_incident(incident, content)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
