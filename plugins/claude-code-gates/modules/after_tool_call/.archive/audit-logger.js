// TOOLS: Bash,Read,Write,Edit,MultiEdit,NotebookEdit,TodoRead,TodoWrite
// WHY: Comprehensive audit trail for every tool call — feeds metacognition,
// workflow analysis, and security forensics. Joel's standing order (2026-04-25).

const fs = require("fs");
const path = require("path");

// Configurable via environment; defaults to workspace logs dir.
const LOG_DIR = process.env.AUDIT_LOG_DIR ||
  path.join(process.env.HOME || "/home/ubu", ".openclaw", "workspace", "logs");
const LOG_FILE = path.join(LOG_DIR, "audit.jsonl");

// Max length for argument values in the log (avoid dumping entire files).
const MAX_ARG_LEN = 500;

// Sensitive patterns to redact from logged arguments.
const REDACT_PATTERNS = [
  /\b(token|api[_-]?key|password|secret|credential|bearer)\b/i,
];

function sanitizeValue(key, value) {
  if (typeof value !== "string") {
    value = JSON.stringify(value);
  }
  // Redact sensitive-looking values.
  for (const pattern of REDACT_PATTERNS) {
    if (pattern.test(key)) {
      return "[REDACTED]";
    }
  }
  // Truncate long values.
  if (value.length > MAX_ARG_LEN) {
    return value.substring(0, MAX_ARG_LEN) + `... [truncated, ${value.length} chars total]`;
  }
  return value;
}

function sanitizeArgs(toolInput) {
  if (!toolInput || typeof toolInput !== "object") return {};
  const clean = {};
  for (const [key, value] of Object.entries(toolInput)) {
    clean[key] = sanitizeValue(key, value);
  }
  return clean;
}

function classifyAction(toolName, toolInput) {
  const cmd = String((toolInput || {}).command || "");
  const filePath = String((toolInput || {}).path || (toolInput || {}).file_path || "");

  // Config changes: writes to config/yaml/json files in sensitive dirs.
  if ((toolName === "Write" || toolName === "Edit" || toolName === "MultiEdit") &&
      /\.(ya?ml|json|toml|conf|ini|env)$/i.test(filePath)) {
    return "config_change";
  }

  // Git operations.
  if (toolName === "Bash" && /\bgit\s+(push|commit|merge|rebase|reset|tag)\b/.test(cmd)) {
    return "git_write";
  }

  // Destructive file ops.
  if (toolName === "Bash" && /\b(rm|trash|unlink|shred)\b/.test(cmd)) {
    return "destructive";
  }

  // Network/external calls.
  if (toolName === "Bash" && /\b(curl|wget|ssh|scp|rsync|docker|kubectl)\b/.test(cmd)) {
    return "external";
  }

  // File reads.
  if (toolName === "Read" || toolName === "TodoRead") {
    return "read";
  }

  // File writes.
  if (toolName === "Write" || toolName === "Edit" || toolName === "MultiEdit" ||
      toolName === "NotebookEdit" || toolName === "TodoWrite") {
    return "write";
  }

  // Shell commands (general).
  if (toolName === "Bash") {
    return "exec";
  }

  return "other";
}

function appendLog(entry) {
  try {
    fs.mkdirSync(LOG_DIR, { recursive: true });
    fs.appendFileSync(LOG_FILE, JSON.stringify(entry) + "\n", "utf-8");
  } catch (err) {
    // Logging should never crash the agent. Swallow errors.
    try {
      fs.appendFileSync(
        path.join(LOG_DIR, "audit-errors.log"),
        `[${new Date().toISOString()}] Failed to write audit log: ${err.message}\n`
      );
    } catch (_) {
      // truly nothing we can do
    }
  }
}

module.exports = function (input) {
  const toolName = input.tool_name || "unknown";
  const toolInput = input.tool_input || {};
  const result = input.result || "";
  const sessionId = process.env.OPENCLAW_SESSION_ID || process.env.SESSION_ID || "unknown";

  const entry = {
    ts: new Date().toISOString(),
    session: sessionId,
    agent: "claude-code",
    tool: toolName,
    action: classifyAction(toolName, toolInput),
    args: sanitizeArgs(toolInput),
    result_len: typeof result === "string" ? result.length : 0,
    result_preview: typeof result === "string"
      ? result.substring(0, 200).replace(/\n/g, "\\n")
      : "",
  };

  appendLog(entry);

  // Never block — this is purely observational.
  return null;
};
