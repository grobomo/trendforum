#!/usr/bin/env python3
"""Teams Conversation Tracker — central tracking for all Teams message flows.

Shared resource for webhooks, polling, manual Graph API, and queue_reply.
Tracks: responses owed, current topics per chat, response metrics.
Persists to JSON state file and logs to local memex wiki.

Architecture:
    - Any message intake path calls tracker.record_message()
    - Any reply path calls tracker.record_response()
    - Periodic sync (cron/heartbeat) calls tracker.sync_from_graph()
    - Memex integration: tracker.publish_to_memex() writes wiki pages

Usage as module:
    from teams_tracker.tracker import TeamsTracker
    t = TeamsTracker()
    t.record_message(chat_id, msg_id, sender, text, source="webhook")
    t.record_response(chat_id, msg_id)
    gaps = t.pending()
    t.publish_to_memex()

Usage as CLI:
    python3 tracker.py record --chat-id <id> --msg-id <id> --sender <name> [--text <preview>] [--source webhook|poller|graph]
    python3 tracker.py respond --chat-id <id> [--msg-id <id>]
    python3 tracker.py pending
    python3 tracker.py stale [--minutes 15]
    python3 tracker.py status
    python3 tracker.py sync
    python3 tracker.py publish
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────

STATE_DIR = Path(__file__).parent / "state"
STATE_FILE = STATE_DIR / "tracker.json"
CONFIG_FILE = Path(__file__).parent.parent / "teams-poller" / "config.json"
MEMEX_WIKI = Path.home() / ".openclaw" / "workspace" / "memex-coconut" / "wiki"

# Bot signatures to filter out
BOT_SIGNATURES = ["--coconut-bot", "🦎 Molty", "🤖 Marvin"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> float:
    return time.time()


def _is_bot(sender: str, text: str = "") -> bool:
    if not sender:
        return True
    for sig in BOT_SIGNATURES:
        if sig.lower() in (sender + " " + text).lower():
            return True
    return False


class TeamsTracker:
    """Central Teams conversation tracker."""

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.data = self._load()

    # ── Persistence ──────────────────────────────────────────

    def _load(self) -> dict:
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "pending": {},      # chat_id:msg_id → message info (awaiting response)
                "responded": {},    # chat_id:msg_id → message info (responded, pruned after 48h)
                "topics": {},       # chat_id → {topic, last_updated, participants}
                "stats": {
                    "total_recorded": 0,
                    "total_responded": 0,
                    "sources": {},   # source → count
                },
                "updated_at": None,
            }

    def _save(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = _now_iso()
        tmp = self.state_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=2)
        tmp.rename(self.state_file)

    # ── Core API ─────────────────────────────────────────────

    def record_message(
        self, chat_id: str, msg_id: str, sender: str,
        text: str = "", source: str = "unknown", label: str = "",
    ):
        """Record an inbound human message that may need a response.

        Called by: webhook server, poller, manual Graph API queries.
        Deduplicates by chat_id:msg_id key.
        """
        if _is_bot(sender, text):
            return

        key = f"{chat_id}:{msg_id}"

        # Skip if already tracked (pending or recently responded)
        if key in self.data["pending"] or key in self.data["responded"]:
            return

        entry = {
            "chat_id": chat_id,
            "msg_id": msg_id,
            "sender": sender,
            "preview": (text or "")[:120],
            "source": source,
            "label": label or self._chat_label(chat_id),
            "recorded_at": _now_epoch(),
            "recorded_iso": _now_iso(),
        }
        self.data["pending"][key] = entry
        self.data["stats"]["total_recorded"] = self.data["stats"].get("total_recorded", 0) + 1
        self.data["stats"].setdefault("sources", {})[source] = \
            self.data["stats"]["sources"].get(source, 0) + 1

        # Update topic tracking
        self._update_topic(chat_id, sender, text)

        self._save()
        log.debug("Recorded: %s from %s in %s via %s", msg_id, sender, entry["label"], source)

    def record_response(self, chat_id: str, msg_id: str = ""):
        """Mark message(s) as responded.

        If msg_id provided, marks that specific message.
        If msg_id omitted, marks ALL pending in that chat (batch response).
        Called by: queue_reply.py, post_reply in teams_service.
        """
        if msg_id:
            key = f"{chat_id}:{msg_id}"
            if key in self.data["pending"]:
                entry = self.data["pending"].pop(key)
                entry["responded_at"] = _now_epoch()
                entry["response_time_s"] = entry["responded_at"] - entry["recorded_at"]
                self.data["responded"][key] = entry
                self.data["stats"]["total_responded"] = \
                    self.data["stats"].get("total_responded", 0) + 1
        else:
            # Mark all pending for this chat
            to_move = [k for k, v in self.data["pending"].items()
                       if v["chat_id"] == chat_id]
            for key in to_move:
                entry = self.data["pending"].pop(key)
                entry["responded_at"] = _now_epoch()
                entry["response_time_s"] = entry["responded_at"] - entry["recorded_at"]
                self.data["responded"][key] = entry
                self.data["stats"]["total_responded"] = \
                    self.data["stats"].get("total_responded", 0) + 1

        # Prune responded older than 48h
        cutoff = _now_epoch() - 172800
        self.data["responded"] = {
            k: v for k, v in self.data["responded"].items()
            if v.get("responded_at", 0) > cutoff
        }

        self._save()

    # ── Topic Tracking ───────────────────────────────────────

    def _update_topic(self, chat_id: str, sender: str, text: str):
        """Lightweight topic tracking per chat."""
        topics = self.data.setdefault("topics", {})
        chat = topics.setdefault(chat_id, {
            "label": self._chat_label(chat_id),
            "participants": [],
            "last_message_preview": "",
            "last_sender": "",
            "last_updated": "",
            "message_count_24h": 0,
        })
        chat["label"] = self._chat_label(chat_id)
        chat["last_sender"] = sender
        chat["last_message_preview"] = (text or "")[:80]
        chat["last_updated"] = _now_iso()
        if sender and sender not in chat["participants"]:
            chat["participants"].append(sender)
        # Keep participants bounded
        chat["participants"] = chat["participants"][-20:]
        chat["message_count_24h"] = chat.get("message_count_24h", 0) + 1

    def get_topics(self) -> dict:
        """Return current topic state per chat."""
        return self.data.get("topics", {})

    # ── Queries ──────────────────────────────────────────────

    def pending(self) -> list[dict]:
        """All messages awaiting response, sorted oldest first."""
        items = list(self.data.get("pending", {}).values())
        items.sort(key=lambda x: x.get("recorded_at", 0))
        return items

    def pending_by_chat(self) -> dict[str, list[dict]]:
        """Pending messages grouped by chat."""
        by_chat = {}
        for msg in self.pending():
            label = msg.get("label", msg["chat_id"][:20])
            by_chat.setdefault(label, []).append(msg)
        return by_chat

    def stale(self, minutes: int = 15) -> list[dict]:
        """Messages pending longer than threshold."""
        cutoff = _now_epoch() - (minutes * 60)
        return [m for m in self.pending() if m["recorded_at"] < cutoff]

    def stats(self) -> dict:
        """Return tracking statistics."""
        s = self.data.get("stats", {})
        responded = self.data.get("responded", {})
        times = [v.get("response_time_s", 0) for v in responded.values()
                 if v.get("response_time_s")]
        avg_response = (sum(times) / len(times) / 60) if times else 0
        return {
            "pending_count": len(self.data.get("pending", {})),
            "responded_48h": len(responded),
            "total_recorded": s.get("total_recorded", 0),
            "total_responded": s.get("total_responded", 0),
            "avg_response_min": round(avg_response, 1),
            "sources": s.get("sources", {}),
        }

    # ── Chat label lookup ────────────────────────────────────

    def _chat_label(self, chat_id: str) -> str:
        """Look up chat label from teams-poller config."""
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
            for c in config.get("chats", []):
                if c.get("id") == chat_id:
                    return c.get("label", chat_id[:20])
        except Exception:
            pass
        return chat_id[:20]

    # ── Graph API sync ───────────────────────────────────────

    def sync_from_graph(self):
        """Backfill tracker by reading recent messages from all chats via Graph API.

        Catches up on gaps from before the tracker existed or after outages.
        """
        # Lazy imports to avoid dependency when used as simple tracker
        msgraph_lib = os.path.expanduser("~/lib/teams-agent")
        if msgraph_lib not in sys.path:
            sys.path.insert(0, msgraph_lib)

        from lib.msgraph.auth import TokenManager
        from lib.msgraph.client import GraphClient
        from lib.msgraph import teams

        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except Exception as e:
            log.error("Cannot load config: %s", e)
            return

        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No Graph token for sync")
            return

        client = GraphClient(token=token)
        bot_signature = config.get("bot_signature", "--coconut-bot")

        synced = 0
        for chat_cfg in config.get("chats", []):
            chat_id = chat_cfg.get("id", "")
            label = chat_cfg.get("label", "?")
            access = chat_cfg.get("access", "read-write")

            if access == "disabled" or not chat_id:
                continue

            try:
                raw = teams.get_chat_messages(
                    client, chat_id, top=15,
                    order_by="createdDateTime desc",
                )
            except Exception as e:
                log.warning("Sync failed for %s: %s", label, e)
                continue

            for msg in raw:
                p = teams.parse_message(msg)
                text = p.get("text", "")
                sender = p.get("sender_name", "")
                msg_id = p.get("message_id", "")
                if sender and text.strip() and bot_signature not in text:
                    self.record_message(
                        chat_id=chat_id, msg_id=msg_id, sender=sender,
                        text=text, source="graph-sync", label=label,
                    )
                elif bot_signature in text:
                    # Mark as our response
                    self.record_response(chat_id)

            synced += 1
            log.info("Synced %s", label)

        log.info("Sync complete — %d chats processed", synced)

    def discover_chats(self):
        """Auto-discover all Teams chats via Graph API and add new ones to config.

        New chats are added as read-only by default. Existing chats (including
        disabled ones) are never modified. This implements the policy:
        'monitor everything, opt-out only for explicitly disabled chats.'
        """
        import requests

        msgraph_lib = os.path.expanduser("~/lib/teams-agent")
        if msgraph_lib not in sys.path:
            sys.path.insert(0, msgraph_lib)

        from lib.msgraph.auth import TokenManager

        tm = TokenManager()
        token = tm.get_token()
        if not token:
            log.error("No Graph token for chat discovery")
            return 0

        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            config = {"chats": []}

        # Get existing chat IDs to avoid duplicates
        existing_ids = {c.get("id", "") for c in config.get("chats", [])}

        headers = {"Authorization": f"Bearer {token}"}
        # Don't expand members on first pass — too slow for large meeting chats
        url = "https://graph.microsoft.com/v1.0/me/chats?$top=50&$select=id,topic,chatType"
        added = 0

        while url:
            try:
                r = requests.get(url, headers=headers, timeout=30)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                log.warning("Chat discovery failed: %s", e)
                break

            for chat in data.get("value", []):
                chat_id = chat.get("id", "")
                if not chat_id or chat_id in existing_ids:
                    continue

                # Build label from topic or chat type
                topic = chat.get("topic", "")
                chat_type = chat.get("chatType", "unknown")
                label = topic if topic else f"{chat_type} chat {chat_id[:20]}"

                new_entry = {
                    "id": chat_id,
                    "label": label or chat_id[:30],
                    "access": "read-only",
                    "section": "auto-discovered",
                    "note": f"Auto-discovered {_now_iso()[:10]}. Change access to read-write to enable replies.",
                }
                config.setdefault("chats", []).append(new_entry)
                existing_ids.add(chat_id)
                added += 1
                log.info("Discovered: %s (%s)", label, chat_id[:30])

            url = data.get("@odata.nextLink")

        if added > 0:
            # Save updated config
            tmp = CONFIG_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(config, f, indent=2)
            tmp.rename(CONFIG_FILE)
            log.info("Added %d new chats to config (read-only)", added)

        return added

    # ── Memex Integration ────────────────────────────────────

    def publish_to_memex(self):
        """Publish tracker state as a memex wiki page.

        Creates/updates wiki/entities/teams-tracker.md in the local
        memex-coconut worktree. NOT synced to trio/shared memex.
        """
        wiki_entities = MEMEX_WIKI / "entities"
        wiki_entities.mkdir(parents=True, exist_ok=True)
        page = wiki_entities / "teams-tracker.md"

        s = self.stats()
        topics = self.get_topics()
        pending = self.pending_by_chat()
        now = datetime.now(timezone.utc)

        lines = [
            "---",
            "title: Teams Conversation Tracker",
            "type: entity",
            f"created: 2026-04-22",
            f"updated: {now.strftime('%Y-%m-%d')}",
            "status: active",
            "source_count: 1",
            "tags: [teams, tracker, conversations, responses]",
            "---",
            "",
            "Central tracker for all Teams conversations — responses owed, current topics, and metrics.",
            f"Auto-updated by tracker.py. [Source: scripts/teams-tracker/tracker.py]",
            "",
            "## Current Stats",
            "",
            f"- Pending responses: **{s['pending_count']}**",
            f"- Responded (48h): {s['responded_48h']}",
            f"- Total recorded: {s['total_recorded']}",
            f"- Total responded: {s['total_responded']}",
            f"- Avg response time: {s['avg_response_min']}m",
            f"- Sources: {json.dumps(s['sources'])}",
            "",
        ]

        if pending:
            lines.append("## Responses Owed")
            lines.append("")
            for label, msgs in pending.items():
                lines.append(f"### {label} ({len(msgs)} pending)")
                for m in msgs:
                    age_min = (_now_epoch() - m["recorded_at"]) / 60
                    lines.append(f"- **{m['sender']}** ({age_min:.0f}m ago): {m['preview']}")
                    lines.append(f"  - via {m['source']}, msg_id: {m['msg_id'][:15]}")
                lines.append("")

        if topics:
            lines.append("## Active Topics")
            lines.append("")
            for chat_id, topic in topics.items():
                lines.append(f"### {topic.get('label', chat_id[:20])}")
                lines.append(f"- Last sender: {topic.get('last_sender', '?')}")
                lines.append(f"- Preview: {topic.get('last_message_preview', '')}")
                lines.append(f"- Participants: {', '.join(topic.get('participants', []))}")
                lines.append(f"- Messages (24h): {topic.get('message_count_24h', 0)}")
                lines.append(f"- Updated: {topic.get('last_updated', '?')}")
                lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*Auto-generated: {now.strftime('%Y-%m-%d %H:%M UTC')}*")

        page.write_text("\n".join(lines))

        # Update memex log
        log_file = MEMEX_WIKI / "log.md"
        if log_file.exists():
            log_entry = (
                f"\n---\n\n"
                f"## [{now.strftime('%Y-%m-%d %H:%M')}] update | Teams tracker published\n"
                f"- Updated: wiki/entities/teams-tracker.md\n"
                f"- Pending: {s['pending_count']}, Responded (48h): {s['responded_48h']}\n"
            )
            with open(log_file, "a") as f:
                f.write(log_entry)

        log.info("Published to memex: %s", page)


# ── CLI ──────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Teams Conversation Tracker")
    sub = parser.add_subparsers(dest="command")

    p_record = sub.add_parser("record", help="Record an inbound message")
    p_record.add_argument("--chat-id", required=True)
    p_record.add_argument("--msg-id", required=True)
    p_record.add_argument("--sender", required=True)
    p_record.add_argument("--text", default="")
    p_record.add_argument("--source", default="manual")
    p_record.add_argument("--label", default="")

    p_respond = sub.add_parser("respond", help="Mark message(s) as responded")
    p_respond.add_argument("--chat-id", required=True)
    p_respond.add_argument("--msg-id", default="")

    sub.add_parser("pending", help="Show all pending messages")

    p_stale = sub.add_parser("stale", help="Show messages pending > N minutes")
    p_stale.add_argument("--minutes", type=int, default=15)

    sub.add_parser("status", help="Show tracker stats")
    sub.add_parser("sync", help="Backfill from Graph API")
    sub.add_parser("discover", help="Auto-discover all Teams chats, add new ones as read-only")
    sub.add_parser("publish", help="Publish to memex wiki")
    sub.add_parser("topics", help="Show current topics per chat")

    args = parser.parse_args()
    t = TeamsTracker()

    if args.command == "record":
        t.record_message(
            chat_id=args.chat_id, msg_id=args.msg_id,
            sender=args.sender, text=args.text,
            source=args.source, label=args.label,
        )
        print(f"📥 Recorded: {args.sender} in {t._chat_label(args.chat_id)} via {args.source}")

    elif args.command == "respond":
        t.record_response(chat_id=args.chat_id, msg_id=args.msg_id)
        print(f"✅ Responded: {t._chat_label(args.chat_id)}")

    elif args.command == "pending":
        pending = t.pending_by_chat()
        if not pending:
            print("No pending messages.")
        else:
            total = sum(len(v) for v in pending.values())
            print(f"📬 {total} pending message(s):\n")
            for label, msgs in pending.items():
                print(f"  *{label}* ({len(msgs)}):")
                for m in msgs:
                    age = (_now_epoch() - m["recorded_at"]) / 60
                    print(f"    • {m['sender']} ({age:.0f}m ago): {m['preview'][:60]}")
                    print(f"      via {m['source']}")

    elif args.command == "stale":
        stale = t.stale(args.minutes)
        if not stale:
            print(f"No messages pending > {args.minutes}m.")
        else:
            print(f"⚠️  {len(stale)} stale message(s) (>{args.minutes}m):")
            for m in stale:
                age = (_now_epoch() - m["recorded_at"]) / 60
                print(f"  🔴 {m['label']}: {m['sender']} ({age:.0f}m ago)")

    elif args.command == "status":
        s = t.stats()
        print("📊 Teams Tracker Status")
        print(f"  Pending: {s['pending_count']}")
        print(f"  Responded (48h): {s['responded_48h']}")
        print(f"  Total recorded: {s['total_recorded']}")
        print(f"  Total responded: {s['total_responded']}")
        print(f"  Avg response: {s['avg_response_min']}m")
        if s['sources']:
            print(f"  By source: {json.dumps(s['sources'])}")

    elif args.command == "sync":
        t.sync_from_graph()
        pending = t.pending()
        if pending:
            print(f"\n{len(pending)} pending message(s) after sync:")
            for m in pending:
                print(f"  ⏳ {m['label']} — {m['sender']}: {m['preview'][:60]}")
        else:
            print("\nAll caught up.")

    elif args.command == "discover":
        added = t.discover_chats()
        if added:
            print(f"🔍 Discovered {added} new chat(s), added as read-only.")
        else:
            print("🔍 No new chats found.")

    elif args.command == "publish":
        t.publish_to_memex()
        print(f"📖 Published to memex: {MEMEX_WIKI / 'entities' / 'teams-tracker.md'}")

    elif args.command == "topics":
        topics = t.get_topics()
        if not topics:
            print("No topics tracked yet.")
        else:
            print("💬 Current Topics:\n")
            for chat_id, topic in topics.items():
                print(f"  *{topic.get('label', chat_id[:20])}*")
                print(f"    Last: {topic.get('last_sender', '?')}: {topic.get('last_message_preview', '')}")
                print(f"    Participants: {', '.join(topic.get('participants', []))}")
                print(f"    Messages (24h): {topic.get('message_count_24h', 0)}")
                print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
