#!/usr/bin/env python3
"""Comms preprocessor — orchestrates classify + route for Teams messages.

Responsibilities:

1. Walk per-chat ``policy.yaml`` files under ``teams/`` to find chats with
   ``monitoring: enabled`` AND ``access: read-write``.
2. For each such chat, pull new messages via the Graph API (bounded by
   last-seen timestamp in ``.teams-preprocessor-state.json``).
3. Classify each message via ``classify.py``.
4. Route by class:

   - **action_required** → create Trello card directly via API (fallback: todo.md)
   - **escalation** → create Trello card with [ESCALATION] prefix + audit log
   - **fyi** → append to ``memory/channels/teams/<chat>.md``
   - **noise** → discard

5. Record every classification for the response gate to look up.

The Graph API call is delegated to ``graph_client.fetch_messages()``; if that
module isn't importable the script falls back to ``--input-file`` /
``--dry-run`` modes for local testing.

Trello integration:
  Cards are created directly via the Trello REST API — no git push roundtrip.
  Auth: keyring ('openclaw/TRELLO_API_KEY', 'openclaw/TRELLO_TOKEN') with
  env var fallback (TRELLO_API_KEY, TRELLO_TOKEN).
  Default list: Coconut Todo (6954d3af836b51597afff8e9).
  If the API call fails, falls back to _append_todo() so data is never lost.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests as _requests  # type: ignore
except ImportError:
    _requests = None  # type: ignore

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import log as audit_log  # noqa: E402
from classify import classify, Classification, clear_cache  # noqa: E402
from config import REPO_ROOT, load_config  # noqa: E402


STATE_PATH = REPO_ROOT / ".teams-preprocessor-state.json"
CLASSIFICATIONS_PATH = REPO_ROOT / ".teams-classifications.json"
ENTITY_ROOT = REPO_ROOT / "memory" / "channels" / "teams"
TEAMS_ROOT = REPO_ROOT / "teams"


# ── State helpers ────────────────────────────────────────────────────────────


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def load_state() -> dict:
    return _load_json(STATE_PATH)


def save_state(state: dict) -> None:
    _save_json(STATE_PATH, state)


def load_classifications() -> dict:
    return _load_json(CLASSIFICATIONS_PATH)


def save_classifications(data: dict) -> None:
    _save_json(CLASSIFICATIONS_PATH, data)


# ── Policy discovery ─────────────────────────────────────────────────────────


@dataclass
class ChatTarget:
    dir_name: str  # e.g. "my-chat"
    chat_id: str  # platform-specific id
    policy: dict


def _read_policy(policy_path: Path) -> dict | None:
    if not policy_path.exists() or yaml is None:
        return None
    try:
        with policy_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):  # type: ignore[attr-defined]
        return None


def discover_targets(cfg: dict) -> list[ChatTarget]:
    """Return chats eligible for classification (monitoring + read-write)."""
    whitelist = {
        s.strip() for s in cfg.get("chat_whitelist", []) if s.strip()
    }
    targets: list[ChatTarget] = []
    if not TEAMS_ROOT.exists():
        return targets

    for chat_dir in sorted(p for p in TEAMS_ROOT.iterdir() if p.is_dir()):
        if whitelist and chat_dir.name not in whitelist:
            continue
        policy = _read_policy(chat_dir / "policy.yaml")
        if not policy:
            continue
        if policy.get("monitoring") != "enabled":
            continue
        if policy.get("access") != "read-write":
            continue
        chat_id = str(policy.get("chat_id") or "").strip()
        if not chat_id:
            continue
        targets.append(
            ChatTarget(
                dir_name=chat_dir.name, chat_id=chat_id, policy=policy
            )
        )
    return targets


# ── Graph fetcher (pluggable) ────────────────────────────────────────────────


def _fetch_messages(chat_id: str, since_iso: str | None) -> list[dict]:
    """Return new messages for a chat. Returns [] if graph client unavailable."""
    try:
        from graph_client import fetch_messages  # type: ignore
    except ImportError:
        return []
    try:
        return fetch_messages(chat_id, since_iso) or []
    except Exception as e:  # noqa: BLE001
        audit_log(
            "PREPROC_GRAPH_ERROR",
            f"teams/{chat_id}",
            f"{type(e).__name__}: {e}",
        )
        return []


# ── Routing ──────────────────────────────────────────────────────────────────

TODO_HEADER_RE = re.compile(r"^##\s+In Progress\s*$", re.M)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_todo(chat_dir: str, todo_text: str, source_tag: str) -> Path:
    """Append a ``- [ ]`` item under ``## In Progress`` in todo.md.

    FALLBACK ONLY — used when the Trello API is unavailable.
    Primary path is _create_trello_card().
    """
    path = TEAMS_ROOT / chat_dir / "todo.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {chat_dir} Tasks\n\n## In Progress\n\n_(none yet)_\n\n"
            f"## Pending\n\n_(none yet)_\n\n## Done\n\n_(none yet)_\n",
            encoding="utf-8",
        )

    content = path.read_text(encoding="utf-8")
    line = (
        f"- [ ] {todo_text} [{source_tag}]"
        f" [assigned:{datetime.now(timezone.utc).date().isoformat()}]"
    )

    header_match = TODO_HEADER_RE.search(content)
    if not header_match:
        new_content = content.rstrip() + f"\n\n## In Progress\n\n{line}\n"
        path.write_text(new_content, encoding="utf-8")
        return path

    sec_start = header_match.end()
    next_header = re.search(r"^##\s+", content[sec_start:], re.M)
    sec_end = (
        sec_start + next_header.start() if next_header else len(content)
    )

    section = content[sec_start:sec_end]
    section = re.sub(
        r"^\s*_\(none yet\)_\s*$", "", section, flags=re.M
    )
    section = section.strip("\n")
    items = [ln for ln in section.splitlines() if ln.strip()]
    items.append(line)
    rebuilt = "\n\n" + "\n".join(items) + "\n\n"

    new_content = content[:sec_start] + rebuilt + content[sec_end:]
    path.write_text(new_content, encoding="utf-8")
    return path


def _append_fyi(chat_dir: str, sender: str, text: str) -> Path:
    """Append an fyi line to memory/channels/teams/<chat_dir>.md."""
    ENTITY_ROOT.mkdir(parents=True, exist_ok=True)
    path = ENTITY_ROOT / f"{chat_dir}.md"
    header = f"# teams/{chat_dir} — FYI Log\n\n"
    if not path.exists():
        path.write_text(header, encoding="utf-8")
    snippet = text.replace("\n", " ").strip()
    if len(snippet) > 300:
        snippet = snippet[:297] + "..."
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- [{_iso_now()}] {sender}: {snippet}\n")
    return path


# ── Trello integration ───────────────────────────────────────────────────────

_TRELLO_BASE = "https://api.trello.com/1"
_TRELLO_DEFAULT_LIST = "6954d3af836b51597afff8e9"  # Coconut Todo


def _trello_auth() -> dict | None:
    """Return Trello auth params from keyring with env var fallback.

    Returns None if credentials are not available.
    """
    key, tok = None, None
    try:
        import keyring as _kr  # type: ignore
        key = _kr.get_password("openclaw", "TRELLO_API_KEY")
        tok = _kr.get_password("openclaw", "TRELLO_TOKEN")
    except Exception:  # noqa: BLE001
        pass
    key = key or os.getenv("TRELLO_API_KEY", "")
    tok = tok or os.getenv("TRELLO_TOKEN", "")
    if not key or not tok:
        return None
    return {"key": key, "token": tok}


def _create_trello_card(
    name: str,
    desc: str,
    list_id: str | None = None,
) -> str | None:
    """Create a Trello card and return its card ID, or None on failure.

    Args:
        name: Card title (e.g. "[teams/coconut-private] Check the logs")
        desc: Card description with source metadata and message preview.
        list_id: Trello list ID. Defaults to Coconut Todo.

    Returns:
        The new card's ID string, or None if creation failed.
    """
    if _requests is None:
        audit_log(
            "TRELLO_CARD_CREATE",
            "teams_preprocessor",
            "SKIP: requests library not available",
        )
        return None

    auth = _trello_auth()
    if auth is None:
        audit_log(
            "TRELLO_CARD_CREATE",
            "teams_preprocessor",
            "SKIP: Trello credentials not configured",
        )
        return None

    target_list = list_id or _TRELLO_DEFAULT_LIST
    payload = {
        "idList": target_list,
        "name": name[:200],  # Trello allows 16k but short names scan better
        "desc": desc,
        "pos": "top",
    }

    try:
        r = _requests.post(
            f"{_TRELLO_BASE}/cards",
            params=auth,
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        card_id = r.json()["id"]
        audit_log(
            "TRELLO_CARD_CREATE",
            "teams_preprocessor",
            f"card={card_id} list={target_list} name={name[:80]}",
        )
        return card_id
    except Exception as exc:  # noqa: BLE001
        audit_log(
            "TRELLO_CARD_CREATE",
            "teams_preprocessor",
            f"FAILED {type(exc).__name__}: {exc}",
        )
        return None


# ── Main loop ────────────────────────────────────────────────────────────────


@dataclass
class RunResult:
    targets: int = 0
    messages_seen: int = 0
    by_class: dict = None  # type: ignore[assignment]
    paths_touched: list[Path] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.by_class is None:
            self.by_class = {
                "action_required": 0,
                "escalation": 0,
                "fyi": 0,
                "noise": 0,
            }
        if self.paths_touched is None:
            self.paths_touched = []


def _build_card_desc(
    source_tag: str,
    sender: str,
    msg: dict,
    result: Classification,
) -> str:
    """Build a standard Trello card description with source metadata."""
    ts = msg.get("timestamp") or _iso_now()
    text = msg.get("text") or ""
    preview = text.replace("\n", " ").strip()
    if len(preview) > 300:
        preview = preview[:297] + "..."
    confidence = getattr(result, "confidence", "n/a")
    reason = getattr(result, "reason", "") or ""
    return (
        f"Source: {source_tag}\n"
        f"Sender: {sender}\n"
        f"Timestamp: {ts}\n"
        f"Classification: {result.cls} (confidence: {confidence}, reason: {reason[:120]})\n"
        f"\n---\nMessage preview:\n{preview}"
    )


def route_message(
    target: ChatTarget,
    msg: dict,
    result: Classification,
    run: RunResult,
) -> None:
    """Apply side effects for one classified message."""
    source_tag = f"teams/{target.dir_name}"
    sender = msg.get("sender") or "unknown"
    text = msg.get("text") or ""

    if result.cls == "action_required":
        todo = result.todo_text or text.strip()
        card_name = f"[{source_tag}] {todo}"
        card_desc = _build_card_desc(source_tag, sender, msg, result)
        card_id = _create_trello_card(card_name, card_desc)
        if card_id:
            audit_log(
                "TRELLO_CARD_CREATE",
                source_tag,
                f"card={card_id} from msg by {sender}: {todo[:80]}",
            )
        else:
            # Fallback: write to todo.md so data is not lost
            audit_log(
                "TRELLO_CARD_CREATE",
                source_tag,
                f"FALLBACK to todo.md — Trello unavailable; from {sender}: {todo[:80]}",
            )
            path = _append_todo(target.dir_name, todo, source_tag)
            run.paths_touched.append(path)
            audit_log(
                "TODO_CREATE",
                source_tag,
                f"fallback from msg by {sender}: {todo[:80]}",
            )

    elif result.cls == "escalation":
        todo = result.todo_text or text.strip()
        card_name = f"[ESCALATION] [{source_tag}] {todo}"
        card_desc = _build_card_desc(source_tag, sender, msg, result)
        card_id = _create_trello_card(card_name, card_desc)
        audit_log(
            "ESCALATION",
            source_tag,
            f"{sender}: signals={result.matched_signals}",
        )
        if card_id:
            audit_log(
                "TRELLO_CARD_CREATE",
                source_tag,
                f"escalation card={card_id} from {sender}: {todo[:80]}",
            )
        else:
            # Fallback: write to todo.md so data is not lost
            audit_log(
                "TRELLO_CARD_CREATE",
                source_tag,
                f"FALLBACK to todo.md — Trello unavailable; escalation from {sender}",
            )
            path = _append_todo(
                target.dir_name, f"[ESCALATION] {todo}", source_tag
            )
            run.paths_touched.append(path)
            audit_log(
                "TODO_CREATE",
                source_tag,
                f"escalation fallback from {sender}: {todo[:80]}",
            )

    elif result.cls == "fyi":
        path = _append_fyi(target.dir_name, sender, text)
        run.paths_touched.append(path)

    run.by_class[result.cls] = run.by_class.get(result.cls, 0) + 1


def record_classification(
    classifications: dict,
    target: ChatTarget,
    msg: dict,
    result: Classification,
) -> None:
    """Update the per-chat classification cache."""
    entry = {
        "class": result.cls,
        "confidence": result.confidence,
        "reason": result.reason,
        "source": result.source,
        "timestamp": msg.get("timestamp") or _iso_now(),
        "sender": msg.get("sender"),
        "message_id": msg.get("id"),
        "preview": (msg.get("text") or "")[:140],
    }
    chat_entry = classifications.setdefault(target.chat_id, {})
    chat_entry["last"] = entry
    chat_entry["chat_dir"] = target.dir_name
    history = chat_entry.setdefault("history", [])
    history.append(entry)
    if len(history) > 20:
        del history[: len(history) - 20]


def process_messages(
    target: ChatTarget,
    messages: list[dict],
    cfg: dict,
    run: RunResult,
    classifications: dict,
    state: dict,
) -> str | None:
    """Process all new messages for a chat. Returns newest timestamp seen."""
    chat_state = state.setdefault(target.chat_id, {})
    last_seen_ts: str | None = chat_state.get("last_seen_ts")
    seen_ids = set(chat_state.get("seen_ids", []))
    newest_ts = last_seen_ts
    new_seen_ids: list[str] = []

    for msg in messages:
        mid = str(msg.get("id") or "")
        if mid and mid in seen_ids:
            continue
        run.messages_seen += 1
        result = classify(msg, cfg)
        record_classification(classifications, target, msg, result)
        route_message(target, msg, result, run)
        if mid:
            new_seen_ids.append(mid)
        ts = msg.get("timestamp")
        if ts and (newest_ts is None or ts > newest_ts):
            newest_ts = ts

    if new_seen_ids:
        seen_ids.update(new_seen_ids)
        chat_state["seen_ids"] = sorted(seen_ids)[-100:]
    if newest_ts:
        chat_state["last_seen_ts"] = newest_ts
    chat_state["last_run"] = _iso_now()
    return newest_ts


def run(
    cfg: dict,
    *,
    messages_by_chat: dict | None = None,
    dry_run: bool = False,
    commit: bool = True,  # kept for API compatibility; no longer used
) -> RunResult:
    """Run one pass of the preprocessor.

    action_required and escalation messages are written directly to Trello
    (with todo.md fallback if the API is unavailable). fyi messages still
    append to memory/channels/teams/<chat>.md. noise is discarded.
    """
    clear_cache()
    run_result = RunResult()
    state = load_state()
    classifications = load_classifications()

    targets = discover_targets(cfg)
    run_result.targets = len(targets)

    if not cfg.get("enabled") and not dry_run:
        audit_log(
            "PREPROC_DISABLED",
            "teams_preprocessor",
            f"enabled=false; discovered {len(targets)} targets; no-op",
        )
        return run_result

    for target in targets:
        if messages_by_chat is not None:
            messages = messages_by_chat.get(target.dir_name, [])
        else:
            since = state.get(target.chat_id, {}).get("last_seen_ts")
            messages = _fetch_messages(target.chat_id, since)
        if not messages:
            continue
        process_messages(
            target, messages, cfg, run_result, classifications, state
        )

    if not dry_run:
        save_state(state)
        save_classifications(classifications)
        # Note: _git_commit() removed — tasks now go directly to Trello.
        # Fallback todo.md writes (paths_touched) are committed by the caller
        # if needed, but are not required for Trello sync.

    audit_log(
        "PREPROC_RUN",
        "teams_preprocessor",
        f"targets={run_result.targets} msgs={run_result.messages_seen} "
        f"by_class={run_result.by_class} dry_run={dry_run}",
    )
    return run_result


# ── CLI ──────────────────────────────────────────────────────────────────────


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Comms preprocessor")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify but skip writes and commits",
    )
    p.add_argument(
        "--input-file",
        type=Path,
        help="JSON file with {chat_dir: [msg,...]} for local testing",
    )
    p.add_argument(
        "--no-commit", action="store_true",
        help="[deprecated] Kept for CLI compatibility; git commits are no longer performed."
    )
    p.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = p.parse_args(argv)

    cfg = load_config()

    messages_by_chat = None
    if args.input_file:
        with args.input_file.open("r", encoding="utf-8") as f:
            messages_by_chat = json.load(f)
        cfg = {**cfg, "enabled": True}

    result = run(
        cfg,
        messages_by_chat=messages_by_chat,
        dry_run=args.dry_run,
        commit=not args.no_commit,
    )

    summary = {
        "targets": result.targets,
        "messages_seen": result.messages_seen,
        "by_class": result.by_class,
        "paths_touched": [str(p) for p in result.paths_touched],
        "enabled": bool(cfg.get("enabled")),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"targets={summary['targets']} "
            f"messages={summary['messages_seen']} "
            f"by_class={summary['by_class']} "
            f"enabled={summary['enabled']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
