#!/usr/bin/env python3
"""GitHub Event Poller for OpenClaw cron.

Polls GitHub repos for new events (issues, PRs, comments, reviews),
builds context, and outputs formatted prompts for OpenClaw to respond to.

State tracked in ~/.openclaw/github-poller/state.json.
Replies posted back via `gh api`.

Usage (standalone test):
    python3 poll_github.py

Usage (via openclaw cron):
    Cron fires a system-event that triggers this script, reads stdout,
    and feeds it to the agent.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [github-poller] %(message)s",
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
STATE_DIR = Path.home() / ".openclaw" / "github-poller"
STATE_FILE = STATE_DIR / "state.json"
REPLY_QUEUE_FILE = STATE_DIR / "reply_queue.json"

GH_BIN = shutil.which("gh") or "gh"

ACTIONABLE_EVENTS = {
    "IssueCommentEvent",
    "IssuesEvent",
    "PullRequestEvent",
    "PullRequestReviewCommentEvent",
    "PullRequestReviewEvent",
    "CommitCommentEvent",
}

DEFAULT_IGNORE_EVENTS = ["ForkEvent", "WatchEvent", "StarEvent"]


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"processed_ids": [], "repo_cache": {}}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["processed_ids"] = state.get("processed_ids", [])[-500:]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── GitHub API ───────────────────────────────────────────────────

def gh_api(*args) -> any:
    """Run gh api command, return parsed JSON or None."""
    cmd = [GH_BIN, "api"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            log.error("gh api error: %s", result.stderr[:300])
            return None
        return json.loads(result.stdout) if result.stdout.strip() else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        log.error("gh command failed: %s", e)
        return None


BOT_MARKER = "<!-- openclaw-bot -->"


def is_own_post(text: str, bot_signature: str) -> bool:
    if not text:
        return False
    if BOT_MARKER in text:
        return True
    sig_plain = bot_signature.replace("*", "").replace("\n", " ").strip()
    return bot_signature in text or sig_plain in text


def post_comment(repo: str, issue_number: int, reply_text: str, bot_signature: str):
    """Post a comment with hidden marker + signature."""
    signed = BOT_MARKER + "\n" + reply_text + bot_signature
    body_json = json.dumps({"body": signed})
    result = subprocess.run(
        [GH_BIN, "api", f"/repos/{repo}/issues/{issue_number}/comments",
         "-X", "POST", "--input", "-",
         "-H", "Accept: application/vnd.github+json"],
        input=body_json, capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        log.info("Posted comment on %s#%s", repo, issue_number)
        return True
    else:
        log.error("Failed to post on %s#%s: %s", repo, issue_number, result.stderr[:200])
        return False


# ── Context builders ─────────────────────────────────────────────

def build_issue_context(repo: str, issue: dict, max_comments: int = 10) -> str:
    """Fetch issue body + recent comments as context."""
    number = issue.get("number")
    parts = [f"Issue #{number} in {repo}: {issue.get('title', '')}"]

    if issue.get("body"):
        parts.append(issue["body"][:2000])

    comments = gh_api(
        f"/repos/{repo}/issues/{number}/comments",
        "--jq", ".",
        "-H", "Accept: application/vnd.github+json",
    )
    if comments and isinstance(comments, list):
        recent = comments[-max_comments:]
        if recent:
            parts.append("\nRecent comments:")
            for c in recent:
                author = c.get("user", {}).get("login", "?")
                cbody = c.get("body", "")[:500]
                if is_own_post(cbody, ""):
                    author += " (bot)"
                parts.append(f"@{author}: {cbody}")

    return "\n".join(parts)


def bot_already_replied_after(repo: str, number: int, after_timestamp: str, bot_signature: str) -> bool:
    """Check if bot already replied to an issue/PR after a given timestamp."""
    comments = gh_api(
        f"/repos/{repo}/issues/{number}/comments",
        "--jq", ".",
        "-H", "Accept: application/vnd.github+json",
    )
    if comments and isinstance(comments, list):
        for c in comments:
            if (is_own_post(c.get("body", ""), bot_signature)
                    and c.get("created_at", "") > after_timestamp):
                return True
    return False


# ── Event formatting ─────────────────────────────────────────────

def format_event(event: dict, config: dict) -> dict | None:
    """Format a GitHub event into a prompt + reply info.

    Returns dict with:
        prompt: str - the text to send to OpenClaw
        repo: str
        number: int | None - issue/PR number for reply
        event_type: str
    Or None if the event should be skipped.
    """
    etype = event.get("type", "")
    payload = event.get("payload", {})
    repo = event.get("repo", {}).get("name", "")
    actor = event.get("actor", {}).get("login", "")
    bot_signature = config.get("bot_signature", "\n\n---\n*openclaw-bot*")
    max_comments = config.get("max_context_comments", 10)

    if etype == "IssueCommentEvent":
        comment = payload.get("comment", {})
        issue = payload.get("issue", {})
        body = comment.get("body", "")

        if is_own_post(body, bot_signature):
            return None

        number = issue.get("number")
        comment_created = comment.get("created_at", "")

        # Check if bot already replied after this comment
        if bot_already_replied_after(repo, number, comment_created, bot_signature):
            log.info("Skipping comment on %s#%s — bot already replied after it", repo, number)
            return None

        context = build_issue_context(repo, issue, max_comments)
        prompt = f"{context}\n\nNew comment by @{actor}:\n{body}"
        return {"prompt": prompt, "repo": repo, "number": number, "event_type": etype}

    elif etype == "IssuesEvent":
        action = payload.get("action", "")
        issue = payload.get("issue", {})

        if action not in ("opened", "reopened"):
            return None
        if is_own_post(issue.get("body", "") or "", bot_signature):
            return None

        number = issue.get("number")

        # Check if bot already replied
        comments = gh_api(
            f"/repos/{repo}/issues/{number}/comments",
            "--jq", ".", "-H", "Accept: application/vnd.github+json",
        )
        if comments and isinstance(comments, list):
            for c in comments:
                if is_own_post(c.get("body", ""), bot_signature):
                    log.info("Skipping issue %s#%s — bot already replied", repo, number)
                    return None

        context = build_issue_context(repo, issue, max_comments)
        labels = ", ".join(l.get("name", "") for l in issue.get("labels", []))
        if labels:
            context += f"\n\nLabels: {labels}"
        return {"prompt": context, "repo": repo, "number": number, "event_type": etype}

    elif etype == "PullRequestEvent":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})

        if action not in ("opened", "reopened"):
            return None
        if is_own_post(pr.get("body", "") or "", bot_signature):
            return None

        number = pr.get("number")

        # Check if bot already replied
        comments = gh_api(
            f"/repos/{repo}/issues/{number}/comments",
            "--jq", ".", "-H", "Accept: application/vnd.github+json",
        )
        if comments and isinstance(comments, list):
            for c in comments:
                if is_own_post(c.get("body", ""), bot_signature):
                    log.info("Skipping PR %s#%s — bot already replied", repo, number)
                    return None

        title = pr.get("title", "")
        body = pr.get("body", "") or ""
        head = pr.get("head", {}).get("ref", "?")
        base = pr.get("base", {}).get("ref", "?")
        additions = pr.get("additions", 0)
        deletions = pr.get("deletions", 0)

        prompt = (
            f"New PR #{number} in {repo}: {title}\n"
            f"Branch: {head} -> {base}, +{additions}/-{deletions}\n\n{body}"
        )
        return {"prompt": prompt, "repo": repo, "number": number, "event_type": etype}

    elif etype in ("PullRequestReviewCommentEvent", "PullRequestReviewEvent"):
        comment = payload.get("comment", {})
        pr = payload.get("pull_request", {})
        body = comment.get("body", "")

        if is_own_post(body, bot_signature):
            return None

        path = comment.get("path", "")
        diff_hunk = comment.get("diff_hunk", "")
        number = pr.get("number")

        prompt = (
            f"PR #{number} review comment by @{actor} in {repo}\n"
            f"File: {path}\n```\n{diff_hunk}\n```\n\nComment: {body}"
        )
        return {"prompt": prompt, "repo": repo, "number": number, "event_type": etype}

    elif etype == "CommitCommentEvent":
        comment = payload.get("comment", {})
        body = comment.get("body", "")

        if is_own_post(body, bot_signature):
            return None

        sha = comment.get("commit_id", "")[:8]
        prompt = f"Commit comment by @{actor} on {sha} in {repo}:\n{body}"
        return {"prompt": prompt, "repo": repo, "number": None, "event_type": etype}

    return None


# ── Repo discovery ───────────────────────────────────────────────

def get_repos(owner: str, state: dict) -> list[str]:
    """Get recently-active repos for the owner."""
    cache = state.get("repo_cache", {})
    now = time.time()

    # Refresh every 5 minutes
    if not cache.get("all") or now - cache.get("fetched_at", 0) > 300:
        result = gh_api(
            "user/repos", "--paginate", "--jq",
            f'[.[] | select(.owner.login == "{owner}") '
            '| {name: .full_name, updated: .updated_at, pushed: .pushed_at}]',
            "-H", "Accept: application/vnd.github+json",
        )
        if result and isinstance(result, list):
            cache = {"all": result, "fetched_at": now}
            state["repo_cache"] = cache
            log.debug("Discovered %d repos for %s", len(result), owner)
        elif not cache.get("all"):
            return []

    # Poll repos updated in the last hour
    import calendar
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
    active = [
        r["name"] for r in cache["all"]
        if r.get("pushed", "") > cutoff or r.get("updated", "") > cutoff
    ]
    return active


# ── Main poll ────────────────────────────────────────────────────

def poll() -> str | None:
    """Poll for new GitHub events. Returns formatted prompt if actionable events found."""
    config = load_config()
    state = load_state()

    owner = config.get("owner", "")
    if not owner:
        log.error("No owner in config.json")
        return None

    bot_signature = config.get("bot_signature", "\n\n---\n*openclaw-bot*")
    ignore_events = set(config.get("ignore_event_types", DEFAULT_IGNORE_EVENTS))
    ignore_actors = set(config.get("ignore_actors", []))
    max_event_age = config.get("max_event_age_seconds", 3600)

    repos = get_repos(owner, state)
    if not repos:
        log.debug("No recently-active repos for %s", owner)
        save_state(state)
        return None

    processed = set(state.get("processed_ids", []))
    all_events = []

    for repo in repos:
        events = gh_api(
            f"repos/{repo}/events?per_page=100",
            "--jq", ".",
            "-H", "Accept: application/vnd.github+json",
        )
        if not events or not isinstance(events, list):
            continue

        for event in events:
            eid = event.get("id", "")
            if eid in processed:
                continue
            etype = event.get("type", "")
            if etype in ignore_events:
                state.setdefault("processed_ids", []).append(eid)
                continue
            actor = event.get("actor", {}).get("login", "")
            if actor in ignore_actors:
                state.setdefault("processed_ids", []).append(eid)
                continue

            # Tag with repo name
            if "repo" not in event or not event["repo"].get("name"):
                event.setdefault("repo", {})["name"] = repo

            all_events.append(event)

    # Dedupe and sort oldest first
    seen = set()
    unique = []
    now_ts = time.time()
    import calendar

    for e in all_events:
        eid = e.get("id", "")
        if eid in seen:
            continue
        seen.add(eid)

        # Skip stale events
        created = e.get("created_at", "")
        if created and max_event_age > 0:
            try:
                evt_ts = calendar.timegm(time.strptime(created, "%Y-%m-%dT%H:%M:%SZ"))
                age = now_ts - evt_ts
                if age > max_event_age:
                    log.info("Skipping stale event %s (%s, age=%dm)", eid, e.get("type", ""), int(age / 60))
                    state.setdefault("processed_ids", []).append(eid)
                    continue
            except (ValueError, OverflowError):
                pass

        unique.append(e)

    unique.sort(key=lambda e: e.get("created_at", ""))

    # Process actionable events
    actionable = []
    for event in unique:
        eid = event.get("id", "")
        etype = event.get("type", "")

        if etype not in ACTIONABLE_EVENTS:
            state.setdefault("processed_ids", []).append(eid)
            continue

        formatted = format_event(event, config)
        if formatted:
            formatted["event_id"] = eid
            actionable.append(formatted)
        else:
            # Skipped (own post, already replied, etc.)
            state.setdefault("processed_ids", []).append(eid)

    if not actionable:
        save_state(state)
        return None

    # Build combined prompt
    parts = []
    parts.append(f"## GitHub Activity — {len(actionable)} new event(s)\n")

    for i, item in enumerate(actionable):
        parts.append(f"### Event {i+1}: {item['event_type']} on {item['repo']}")
        parts.append(item["prompt"])
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("Respond to each event that needs a reply. For each reply, clearly indicate:")
    parts.append("GITHUB_REPLY repo=<repo> number=<number>")
    parts.append("<your reply text>")
    parts.append("GITHUB_END_REPLY")
    parts.append("")
    parts.append("If an event doesn't need a reply, skip it.")
    parts.append("If NONE need a reply, respond with just: GITHUB_NO_REPLY")

    # Store pending events for reply routing
    state["pending_events"] = [
        {"event_id": a["event_id"], "repo": a["repo"], "number": a["number"]}
        for a in actionable
    ]

    # Mark all as processed now (we've formatted them)
    for a in actionable:
        state.setdefault("processed_ids", []).append(a["event_id"])

    save_state(state)
    return "\n".join(parts)


def post_replies(reply_text: str, config: dict | None = None):
    """Parse structured replies and post them to GitHub."""
    if not config:
        config = load_config()
    bot_signature = config.get("bot_signature", "\n\n---\n*openclaw-bot*")

    import re
    pattern = r'GITHUB_REPLY\s+repo=(\S+)\s+number=(\d+)\s*\n(.*?)GITHUB_END_REPLY'
    matches = re.findall(pattern, reply_text, re.DOTALL)

    posted = 0
    for repo, number_str, body in matches:
        number = int(number_str)
        body = body.strip()
        if body and body not in ("NO_REPLY", "HEARTBEAT_OK"):
            if post_comment(repo, number, body, bot_signature):
                posted += 1

    return posted


if __name__ == "__main__":
    result = poll()
    if result:
        print(result)
    else:
        log.info("No new actionable events")
