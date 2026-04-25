// TOOLS: Bash, write, edit
// WHY: Coconut starts work without tracking it in todo.md. Joel can't trust
// work is being done because there's no trail. Every action must be tracked
// in the relevant openclaw-dm todo.md file FIRST.
//
// This gate blocks tool calls that look like "doing work" (writing code,
// running scripts, making API calls) unless the session has already read
// a todo.md file. It's a forcing function: read your task list before acting.

const fs = require("node:fs");
const path = require("node:path");

// Tools that represent "doing work" (not just reading/checking)
const WORK_TOOLS = ["write", "edit", "exec"];

// Commands that are exempt (reading, checking, not doing)
const EXEMPT_PATTERNS = [
  /\bcat\b/,
  /\bls\b/,
  /\bhead\b/,
  /\btail\b/,
  /\bgrep\b/,
  /\bfind\b/,
  /\bwc\b/,
  /\bdu\b/,
  /\bdf\b/,
  /\bpwd\b/,
  /\bwhoami\b/,
  /\becho\b/,
  /\bwhich\b/,
  /\btimeout\s+\d+\s+openclaw/,
  /\bopenclaw\s+(cron|status|sessions|help)/,
  /\bpython3\s+-c\s+"import keyring/,  // credential lookups
  /\bcurl\s+-s\s+"https:\/\/api\.trello/,  // trello reads
  /\bgit\s+(status|log|diff|branch)/,
  /\bpython3\s+.*monitor\.py/,  // health monitors
  /\bpython3\s+.*self-audit\.py/,  // self-audit
  /\bpython3\s+.*state_manager\.py/,  // slack state check
  /todo\.md/,  // reading todo files is always ok
  /HEARTBEAT/,
  /MEMORY/,
  /memory\//,
];

// Files that are exempt from write/edit (config, memory, metacognition)
const EXEMPT_PATHS = [
  /todo\.md/,
  /MEMORY\.md/,
  /HEARTBEAT\.md/,
  /AGENTS\.md/,
  /memory\//,
  /metacognition\//,
  /\.archive\//,
  /sessions\.json/,
  /\/tmp\//,
];

// Track whether todo.md has been read this session via a state file
const STATE_FILE = "/tmp/coconut-todo-read-session.json";

function hasTodoBeenRead() {
  try {
    if (!fs.existsSync(STATE_FILE)) return false;
    const state = JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
    // Valid for 30 minutes (covers one autonomous cycle)
    const age = Date.now() - (state.timestamp || 0);
    return age < 30 * 60 * 1000;
  } catch {
    return false;
  }
}

function markTodoRead() {
  fs.writeFileSync(STATE_FILE, JSON.stringify({
    timestamp: Date.now(),
    read: true
  }));
}

module.exports = function(input) {
  const toolName = (input.tool_name || "").toLowerCase();
  const params = input.tool_input || {};

  // Only gate work tools
  if (!WORK_TOOLS.includes(toolName)) return null;

  // Check if this is a read of todo.md — if so, mark it and allow
  if (toolName === "exec") {
    const cmd = String(params.command || "");
    if (/todo\.md/.test(cmd) && /\b(cat|read|head|less)\b/.test(cmd)) {
      markTodoRead();
      return null;
    }
    // Check exempt command patterns
    for (const pattern of EXEMPT_PATTERNS) {
      if (pattern.test(cmd)) return null;
    }
  }

  if (toolName === "write" || toolName === "edit") {
    const filePath = String(params.path || params.file_path || "");
    // Writing TO a todo.md = tracking work = allowed + mark as read
    if (/todo\.md/.test(filePath)) {
      markTodoRead();
      return null;
    }
    // Exempt paths (memory, config, etc.)
    for (const pattern of EXEMPT_PATHS) {
      if (pattern.test(filePath)) return null;
    }
  }

  // If todo has been read recently, allow
  if (hasTodoBeenRead()) return null;

  // Block: doing work without reading todo
  return {
    decision: "block",
    reason:
      "TODO ENFORCEMENT: You're doing work without reading your task list first.\n\n" +
      "Before doing any work, you MUST:\n" +
      "1. Read the relevant todo.md file (e.g., ~/openclaw-dm/dm/todo.md)\n" +
      "2. Check if a todo item exists for this work\n" +
      "3. If not, CREATE a todo item first, THEN do the work\n\n" +
      "This ensures every action is tracked and visible.\n" +
      "Read a todo.md file now, then retry your action.",
  };
};
