#!/usr/bin/env python3
"""Brain MCP Server — exposes unified-brain REST API as MCP tools.

Implements the Model Context Protocol (MCP) over stdio (JSON-RPC 2.0).
Talks to the brain's HTTP API on the host machine.

Usage:
    python3 brain_mcp.py [--brain-url http://HOST:8790]

OpenClaw config:
    "mcp": {
        "servers": {
            "brain": {
                "command": "python3",
                "args": ["/path/to/brain_mcp.py", "--brain-url", "http://172.17.128.1:8790"]
            }
        }
    }
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
import urllib.parse


BRAIN_URL = "http://localhost:8790"


def _brain_get(path: str, params: dict = None) -> dict:
    """GET request to brain API."""
    url = BRAIN_URL + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": f"Connection failed: {e}"}


def _brain_post(path: str, body: dict) -> tuple[int, dict]:
    """POST request to brain API. Returns (status_code, response_dict)."""
    url = BRAIN_URL + path
    data = json.dumps(body).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 0, {"error": f"Connection failed: {e}"}


# --- MCP Tool definitions ---

TOOLS = [
    {
        "name": "brain_ask",
        "description": "Ask the brain a question with full cross-channel context and conversation history. Use for natural language queries about repos, issues, teams, customers, project status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask the brain"},
                "author": {"type": "string", "description": "Who is asking (for conversation history)", "default": "openclaw"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "brain_search",
        "description": "Full-text search across all events in the brain (GitHub issues, Teams messages, webhook events). Returns matching events ranked by relevance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms (FTS5 syntax supported)"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_events",
        "description": "List recent events from the brain's event store. Filter by source (github/teams/webhook), channel, author, or time window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Filter by source: github, teams, webhook, signal"},
                "channel": {"type": "string", "description": "Filter by channel (repo name, chat ID)"},
                "author": {"type": "string", "description": "Filter by author"},
                "hours": {"type": "integer", "description": "Look back this many hours", "default": 24},
                "limit": {"type": "integer", "description": "Max events to return", "default": 50},
            },
        },
    },
    {
        "name": "brain_store",
        "description": "Store a new event in the brain. Use to log notes, customer updates, task completions, or any information that should be searchable later.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Event source (e.g. 'signal', 'note')", "default": "openclaw"},
                "channel": {"type": "string", "description": "Channel identifier", "default": "signal-dm"},
                "event_type": {"type": "string", "description": "Type: note, task, update, message", "default": "note"},
                "author": {"type": "string", "description": "Who created this"},
                "title": {"type": "string", "description": "Short title"},
                "body": {"type": "string", "description": "Full content"},
                "metadata": {"type": "object", "description": "Additional key-value data"},
            },
            "required": ["body"],
        },
    },
    {
        "name": "brain_memory",
        "description": "Read the brain's memory summaries — project-level and global patterns. Shows aggregated insights from all monitored channels.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter to a specific project name"},
            },
        },
    },
    {
        "name": "teams_chats",
        "description": "List Microsoft Teams chats. Optionally filter by topic name. Returns chat IDs, topics, and last message preview.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Filter chats by topic (case-insensitive substring match)"},
            },
        },
    },
    {
        "name": "teams_read",
        "description": "Read recent messages from a Microsoft Teams chat. Returns sender, timestamp, and message body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Teams chat ID (from teams_chats)"},
                "limit": {"type": "integer", "description": "Max messages to return", "default": 20},
            },
            "required": ["chat_id"],
        },
    },
    {
        "name": "teams_send",
        "description": "Send a message to a Microsoft Teams chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Teams chat ID (from teams_chats)"},
                "message": {"type": "string", "description": "Message text to send"},
            },
            "required": ["chat_id", "message"],
        },
    },
]


def _handle_tool_call(name: str, arguments: dict) -> list[dict]:
    """Execute a tool call and return MCP content blocks."""
    if name == "brain_ask":
        _, result = _brain_post("/ask", {
            "question": arguments["question"],
            "source": "signal",
            "author": arguments.get("author", "openclaw"),
            "channel": "signal-dm",
            "format": "signal",
        })
        text = result.get("text", result.get("content", json.dumps(result)))
        return [{"type": "text", "text": text}]

    elif name == "brain_search":
        result = _brain_get("/search", {
            "q": arguments["query"],
            "limit": arguments.get("limit", 20),
        })
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        results = result.get("results", [])
        if not results:
            return [{"type": "text", "text": f"No results for '{arguments['query']}'"}]
        lines = [f"Found {len(results)} results for '{arguments['query']}':\n"]
        for ev in results:
            title = ev.get("title", "")
            body = (ev.get("body", "") or "")[:200]
            lines.append(f"- [{ev.get('source')}:{ev.get('channel')}] {title or body}")
        return [{"type": "text", "text": "\n".join(lines)}]

    elif name == "brain_events":
        params = {}
        for key in ("source", "channel", "author", "hours", "limit"):
            if key in arguments:
                params[key] = arguments[key]
        result = _brain_get("/events", params)
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        events = result.get("events", [])
        if not events:
            return [{"type": "text", "text": "No events found matching filters."}]
        lines = [f"{result.get('count', len(events))} events:\n"]
        for ev in events:
            title = ev.get("title", "")
            body = (ev.get("body", "") or "")[:100]
            lines.append(f"- [{ev.get('source')}:{ev.get('channel')}] {ev.get('event_type')}: {title or body}")
        return [{"type": "text", "text": "\n".join(lines)}]

    elif name == "brain_store":
        _, result = _brain_post("/events", {
            "source": arguments.get("source", "openclaw"),
            "channel": arguments.get("channel", "signal-dm"),
            "event_type": arguments.get("event_type", "note"),
            "author": arguments.get("author"),
            "title": arguments.get("title", ""),
            "body": arguments["body"],
            "metadata": arguments.get("metadata"),
        })
        if "error" in result:
            return [{"type": "text", "text": f"Error storing event: {result['error']}"}]
        return [{"type": "text", "text": f"Stored event: {result.get('event_id', 'ok')}"}]

    elif name == "brain_memory":
        params = {}
        if "project" in arguments:
            params["project"] = arguments["project"]
        result = _brain_get("/memory", params)
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        return [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]

    elif name == "teams_chats":
        params = {}
        if "topic" in arguments:
            params["topic"] = arguments["topic"]
        result = _brain_get("/teams/chats", params)
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        chats = result.get("chats", [])
        if not chats:
            return [{"type": "text", "text": "No Teams chats found."}]
        lines = [f"{len(chats)} chats:\n"]
        for c in chats:
            lines.append(f"- [{c.get('chatType')}] {c.get('topic')}  (id: {c.get('id', '')[:20]}...)")
            if c.get("lastMessage"):
                lines.append(f"  Last: {c['lastMessage']}")
        return [{"type": "text", "text": "\n".join(lines)}]

    elif name == "teams_read":
        params = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        result = _brain_get(f"/teams/chats/{arguments['chat_id']}/messages", params)
        if "error" in result:
            return [{"type": "text", "text": f"Error: {result['error']}"}]
        msgs = result.get("messages", [])
        if not msgs:
            return [{"type": "text", "text": "No messages in this chat."}]
        lines = [f"{len(msgs)} messages:\n"]
        for m in msgs:
            lines.append(f"[{m.get('timestamp')}] {m.get('sender')}: {m.get('body', '')[:200]}")
        return [{"type": "text", "text": "\n".join(lines)}]

    elif name == "teams_send":
        _, result = _brain_post(f"/teams/chats/{arguments['chat_id']}/send", {
            "message": arguments["message"],
        })
        if "error" in result:
            return [{"type": "text", "text": f"Error sending: {result['error']}"}]
        return [{"type": "text", "text": f"Message sent to Teams chat."}]

    return [{"type": "text", "text": f"Unknown tool: {name}"}]


# --- MCP JSON-RPC protocol ---

def _send(msg: dict):
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(msg)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _handle_message(msg: dict) -> dict | None:
    """Handle a single JSON-RPC message. Returns response or None for notifications."""
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "brain-mcp", "version": "1.0.0"},
            },
        }

    elif method == "notifications/initialized":
        return None  # Notification, no response

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            content = _handle_tool_call(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": content, "isError": False},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Tool error: {e}"}],
                    "isError": True,
                },
            }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    elif msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    return None


def main():
    parser = argparse.ArgumentParser(description="Brain MCP Server")
    parser.add_argument("--brain-url", default="http://localhost:8790",
                        help="Brain REST API URL (default: http://localhost:8790)")
    args = parser.parse_args()

    global BRAIN_URL
    BRAIN_URL = args.brain_url.rstrip("/")

    # Read JSON-RPC messages from stdin, one per line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = _handle_message(msg)
        if response is not None:
            _send(response)


if __name__ == "__main__":
    main()
