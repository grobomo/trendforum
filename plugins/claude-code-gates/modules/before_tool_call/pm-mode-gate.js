// WHY: The Opus 'trello-work' cron is meant to be Coconut's project-manager
//      loop: pull Trello cards, manage Claude Code worker tabs, send Slack
//      updates, and DELEGATE all building/coding to Claude Code sessions.
//      Without enforcement, Opus keeps doing the work itself — expensive,
//      slow, and conflates PM and IC roles. This gate restricts the
//      trello-work context to PM-only actions.
//      Joel P0 card, 2026-04-25.
//
// No `// TOOLS:` metadata — the gate runs on every tool call so unknown
// tools default to deny in PM mode (default-allow elsewhere).
//
// Allowed in PM mode:
//   read / image / pdf                          → load any context
//   message                                     → Slack updates
//   sessions_spawn / sessions_send / sessions_* → Claude Code session mgmt
//   subagents                                   → delegate to subagents
//   memory_search / memory_get / memory_*       → context recall
//   exec → manage.py                            → Claude Code tab management
//   exec → curl https://api.trello.com/...      → Trello API
//   exec → trello-api.py                        → structured Trello wrapper
//   exec → secret-tool lookup ... openclaw      → creds for Trello API
//
// Blocked in PM mode:
//   write / edit                                → no direct file mutations
//   exec (anything else)                        → no direct shell work
//   web_fetch / web_search / other unknown tool → not PM tools

// ── Context detection ─────────────────────────────────────────────────────

const PM_CRON_PATTERN = /trello[-_]?work/i;

const PM_CONTEXT_VARS = [
  "OPENCLAW_CRON_NAME",
  "OPENCLAW_CRON_ID",
  "OPENCLAW_CRON_LABEL",
  "OPENCLAW_CRON_JOB",
  "OPENCLAW_SESSION_LABEL",
  "OPENCLAW_AGENT_CONTEXT",
  "CRON_NAME",
];

function inPmCron() {
  for (const key of PM_CONTEXT_VARS) {
    const v = process.env[key];
    if (typeof v === "string" && PM_CRON_PATTERN.test(v)) return true;
  }
  // Explicit session-context override (set by harness or operator)
  const flag = (process.env.PM_MODE || "").toLowerCase();
  if (flag === "1" || flag === "true" || flag === "trello-work") return true;
  return false;
}

// ── Allowlists ────────────────────────────────────────────────────────────

// PM-mode allowed tool names (OpenClaw-style). Pass through with no further
// inspection. The harness's tool naming is lowercase snake_case for native
// tools; we accept both `sessions_*` family and `subagents`.
const ALLOWED_TOOLS = new Set([
  "read",
  "image",
  "pdf",
  "message",
  "sessions_spawn",
  "sessions_send",
  "sessions_list",
  "sessions_history",
  "sessions_yield",
  "sessions_status",
  "session_status",
  "subagents",
  "memory_search",
  "memory_get",
  "memory_write",
  "agents_list",
  "tts",
  "canvas",
]);

// Bash/exec command allowlist — ONLY manage.py and Trello API per spec.
// Credential lookups are included because Trello API curls require them.
const ALLOWED_EXEC_PATTERNS = [
  /(?:^|[\s/])manage\.py\b/,
  /(?:^|[\s/])manage-claude-code\.py\b/,
  /\bcurl\b[^\n]*\bapi\.trello\.com\b/,
  /(?:^|[\s/])trello-api\.py\b/,
  /\bsecret-tool\s+lookup\b[^\n]*\bopenclaw\b/,
];

// File mutation tools — always blocked in PM mode (delegate, don't code).
const FILE_MUTATION_TOOLS = new Set(["write", "edit", "multiedit", "notebookedit"]);

// MCP tool name fragments allowed in PM mode (memory recall, messaging,
// Trello, session orchestration). Other MCP tools are blocked.
const MCP_ALLOW_FRAGMENTS = ["memory", "message", "slack", "trello", "session", "subagent", "mcpm"];

// ── Main ──────────────────────────────────────────────────────────────────

module.exports = function (input) {
  if (!inPmCron()) return null;

  const rawName = String(input.tool_name || "");
  const toolName = rawName.toLowerCase();
  const params = input.tool_input || {};

  if (ALLOWED_TOOLS.has(toolName)) return null;

  // MCP tools (mcp__server__method) — allow recall/messaging-related ones.
  if (toolName.startsWith("mcp__") || toolName.startsWith("mcp-")) {
    for (const frag of MCP_ALLOW_FRAGMENTS) {
      if (toolName.includes(frag)) return null;
    }
    return {
      decision: "block",
      reason:
        `PM MODE GATE → MCP tool "${rawName}" is not allowed in trello-work\n` +
        "(PM-only) mode. Allowed MCP fragments: memory, message, slack, trello,\n" +
        "session, subagent. Delegate other work to Claude Code via sessions_spawn.",
    };
  }

  // Exec / Bash → command-level allowlist
  if (toolName === "exec" || toolName === "bash") {
    const cmd = String(params.command || "");
    for (const re of ALLOWED_EXEC_PATTERNS) {
      if (re.test(cmd)) return null;
    }
    return {
      decision: "block",
      reason:
        "PM MODE GATE → exec blocked in trello-work cron.\n" +
        "WHY: This Opus cron is PM-only. Coconut delegates building work\n" +
        "to Claude Code; it does not run arbitrary shell commands.\n" +
        "Allowed exec:\n" +
        "  • manage.py (Claude Code tab management)\n" +
        "  • curl https://api.trello.com/... (Trello API)\n" +
        "  • trello-api.py (structured Trello wrapper)\n" +
        "  • secret-tool lookup ... openclaw (creds for Trello API)\n" +
        "BLOCKED: " + cmd.slice(0, 200) + "\n" +
        "REQUIRED: Spawn a Claude Code session via sessions_spawn with a\n" +
        "clear spec; let it run shell/build/code work and return the result.",
    };
  }

  if (FILE_MUTATION_TOOLS.has(toolName)) {
    return {
      decision: "block",
      reason:
        `PM MODE GATE → ${rawName} blocked in trello-work cron.\n` +
        "WHY: PMs delegate, they don't code. Direct file modifications are\n" +
        "forbidden in PM mode.\n" +
        "REQUIRED: Spawn a Claude Code session via sessions_spawn with the\n" +
        "file change spec. The session writes the files; you read the result\n" +
        "and update Trello.",
    };
  }

  return {
    decision: "block",
    reason:
      `PM MODE GATE → tool "${rawName}" is not allowed in trello-work\n` +
      "(PM-only) mode. Allowed actions: read, message, sessions_*, subagents,\n" +
      "memory_*, exec (manage.py / Trello API only). Delegate building work\n" +
      "to Claude Code via sessions_spawn.",
  };
};
