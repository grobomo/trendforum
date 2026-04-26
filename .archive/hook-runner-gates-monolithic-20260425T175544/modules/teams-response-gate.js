/**
 * teams-response-gate — before_tool_call gate
 *
 * Blocks attempts to send a Teams reply (via `queue_reply.py`) when:
 *   1. The target chat's most recent classification is `noise` or `fyi` —
 *      these messages should not be replied to.
 *   2. No unchecked todo item exists for the target chat in
 *      teams/<chat>/todo.md — must track work before sending.
 *
 * Classifications are written by scripts/teams_preprocessor.py to
 * `~/openclaw-dm/.teams-classifications.json`, keyed by chat_id.
 *
 * Wiring into hook-runner-gates/index.ts:
 *   1. Import: const { teamsResponseGate } = require("./modules/teams-response-gate.js");
 *      (or rewrite as TS and inline like other gates)
 *   2. Add to `beforeToolCallGates`:
 *        "teams-response-gate": teamsResponseGate,
 *   3. Add to `openclaw.plugin.json` -> configSchema.modules and config.modules:
 *        "teams-response-gate": { "type": "boolean", "default": true }
 *
 * Signature: (toolName, params) -> string | null
 *   - returns a block reason (string) to block
 *   - returns null to allow
 */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

const REPO_ROOT =
  process.env.OPENCLAW_DM_ROOT || path.join(os.homedir(), "openclaw-dm");
const CLASSIFICATIONS_PATH = path.join(REPO_ROOT, ".teams-classifications.json");
const TEAMS_ROOT = path.join(REPO_ROOT, "teams");

// Chat-id args we understand on the queue_reply.py command line.
// Accepts: --chat-id VAL, --chat-id=VAL, --chat VAL, --chat=VAL, --to VAL.
const CHAT_ID_FLAG_RE = /--(?:chat(?:-id)?|to)(?:=|\s+)(['"]?)([^'"\s]+)\1/;

// Match `- [ ]` lines (unchecked todo) in markdown.
const UNCHECKED_TODO_RE = /^\s*-\s*\[\s\]\s+/m;

function safeReadJson(p) {
  try {
    if (!fs.existsSync(p)) return null;
    const raw = fs.readFileSync(p, "utf-8");
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function extractChatId(cmd) {
  if (!cmd) return null;
  const m = cmd.match(CHAT_ID_FLAG_RE);
  return m ? m[2] : null;
}

function isQueueReplyCall(toolName, params) {
  if (toolName !== "Bash" && toolName !== "exec") return false;
  const cmd = String(params.command || params.cmd || "");
  if (!cmd) return false;
  // Match `queue_reply.py` as a command token (not inside a string literal
  // like `echo "queue_reply.py"`).
  if (!/\bqueue_reply\.py\b/.test(cmd)) return false;
  return cmd;
}

function hasUncheckedTodo(chatDir) {
  const todoPath = path.join(TEAMS_ROOT, chatDir, "todo.md");
  if (!fs.existsSync(todoPath)) return false;
  try {
    const content = fs.readFileSync(todoPath, "utf-8");
    // Cheap check: any `- [ ]` line outside the Done section.
    const doneIdx = content.search(/^##\s+Done\s*$/m);
    const scanRegion = doneIdx >= 0 ? content.slice(0, doneIdx) : content;
    return UNCHECKED_TODO_RE.test(scanRegion);
  } catch (_) {
    return false;
  }
}

function teamsResponseGate(toolName, params) {
  const cmd = isQueueReplyCall(toolName, params);
  if (!cmd) return null;

  const chatId = extractChatId(cmd);
  if (!chatId) {
    return (
      "BLOCKED: queue_reply.py call missing --chat-id. " +
      "teams-response-gate cannot verify classification without a chat id."
    );
  }

  const classifications = safeReadJson(CLASSIFICATIONS_PATH);
  if (!classifications || !classifications[chatId]) {
    return (
      `BLOCKED: no classification found for chat ${chatId}. ` +
      "Run scripts/teams_preprocessor.py so the message is classified before replying."
    );
  }

  const entry = classifications[chatId];
  const last = entry.last || {};
  const chatDir = entry.chat_dir;
  const cls = last.class;

  if (cls === "noise") {
    return (
      `BLOCKED: last message in ${chatDir || chatId} classified as noise — no reply needed.`
    );
  }
  if (cls === "fyi") {
    return (
      `BLOCKED: last message in ${chatDir || chatId} classified as fyi — log it, don't reply.`
    );
  }

  if (!chatDir) {
    return (
      `BLOCKED: classification for ${chatId} is missing chat_dir; preprocessor state is stale.`
    );
  }

  if (!hasUncheckedTodo(chatDir)) {
    return (
      `BLOCKED: no unchecked todo item in teams/${chatDir}/todo.md. ` +
      "Create a todo item first, then reply."
    );
  }

  return null;
}

module.exports = {
  name: "teams-response-gate",
  teamsResponseGate,
  // Expose helpers for unit testing
  _internals: {
    extractChatId,
    isQueueReplyCall,
    hasUncheckedTodo,
    safeReadJson,
    CLASSIFICATIONS_PATH,
    TEAMS_ROOT,
  },
};
