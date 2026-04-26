// TOOLS: exec, write, edit
// WHY: Coconut starts work without tracking it. Sessions compact, work gets
// abandoned silently. This gate enforces that a specific task is registered
// (via .active-task.json) before any "doing work" tool calls are allowed.
// Joel P0 card 2026-04-25: "block actions unless todo item tracked first"
//
// Flow:
//   1. Agent picks up task from Trello/todo.md
//   2. Agent writes .active-task.json with task details
//   3. Gate allows work tool calls
//   4. Agent completes task, clears or replaces .active-task.json
//
// Without step 2, step 3 is blocked. This is the structural enforcement.

const fs = require("node:fs");
const path = require("node:path");

// Where the active task registration lives (workspace = survives compaction)
const WORKSPACE = process.env.OPENCLAW_WORKSPACE
  || path.join(require("node:os").homedir(), ".openclaw", "workspace");
const ACTIVE_TASK_FILE = path.join(WORKSPACE, ".active-task.json");

// Max age for a task registration (4 hours — covers a long work session)
const MAX_AGE_MS = 4 * 60 * 60 * 1000;

// Tools that represent "doing work" (not just reading/checking)
const WORK_TOOLS = ["exec", "write", "edit"];

// ── Exempt command patterns (reads, checks, monitoring — not "work") ────
const EXEMPT_CMD_PATTERNS = [
  // Basic reads
  /^\s*(cat|head|tail|less|more|wc|du|df|ls|find|grep|awk|sed|pwd|whoami|which|echo|date|file)\b/,
  // Git reads
  /\bgit\s+(status|log|diff|branch|show|remote|tag)\b/,
  // OpenClaw system commands
  /\bopenclaw\s+(cron|status|sessions|help|gateway)\b/,
  // Python credential lookups
  /\bpython3?\s+-c\s+["']import keyring/,
  // Trello API reads (checking cards)
  /\bcurl\s.*api\.trello\.com/,
  /\bpython3?\s+.*\bgather\.py\b/,
  // Monitoring scripts
  /\bpython3?\s+.*\bmonitor\.py\b/,
  /\bpython3?\s+.*\bself-audit\.py\b/,
  /\bpython3?\s+.*\bstate_manager\.py\b/,
  // Secret/credential reads
  /\bsecret-tool\s+lookup\b/,
  // Task registration helper
  /\.active-task\.json/,
  // Heartbeat/memory reads
  /HEARTBEAT|MEMORY\.md|memory\//,
  // npm/node reads
  /\bnpm\s+(list|ls|info|view)\b/,
  // Process management reads
  /\bps\b|\bjobs\b|\bsystemctl\s+status\b|\bjournalctl\b/,
];

// ── Exempt file paths (config, memory, task registration, temp) ─────────
const EXEMPT_PATH_PATTERNS = [
  /\.active-task\.json$/,           // task registration itself
  /todo\.md$/i,                     // todo files
  /MEMORY\.md$/,                    // long-term memory
  /HEARTBEAT\.md$/,                 // heartbeat config
  /AGENTS\.md$/,                    // agent config
  /memory\//,                       // daily memory files
  /metacognition\//,                // metacognition logs
  /\.archive\//,                    // archives
  /sessions\.json$/,               // session state
  /\/tmp\//,                        // temp files
  /heartbeat-state\.json$/,        // heartbeat state
  /schedule-briefing/,             // schedule data
  /\.log$/,                         // log files
];

// ── Check if running in a cron/isolated context ─────────────────────────
function isIsolatedSession() {
  // Cron jobs and isolated sessions shouldn't need task tracking
  const agent = process.env.OPENCLAW_AGENT || "";
  if (agent === "isolated" || agent === "cron") return true;
  // Also check if there's a cron marker
  if (process.env.OPENCLAW_CRON_JOB) return true;
  return false;
}

// ── Read active task ────────────────────────────────────────────────────
function getActiveTask() {
  try {
    if (!fs.existsSync(ACTIVE_TASK_FILE)) return null;
    const data = JSON.parse(fs.readFileSync(ACTIVE_TASK_FILE, "utf-8"));
    // Check age
    const age = Date.now() - (data.registered || 0);
    if (age > MAX_AGE_MS) return null; // expired
    if (!data.name) return null; // invalid
    return data;
  } catch {
    return null;
  }
}

module.exports = function (input) {
  const toolName = (input.tool_name || "").toLowerCase();
  const params = input.tool_input || {};

  // Only gate work tools
  if (!WORK_TOOLS.includes(toolName)) return null;

  // Skip in isolated/cron sessions
  if (isIsolatedSession()) return null;

  // Check exec exemptions
  if (toolName === "exec") {
    const cmd = String(params.command || "");
    for (const pattern of EXEMPT_CMD_PATTERNS) {
      if (pattern.test(cmd)) return null;
    }
  }

  // Check write/edit exemptions
  if (toolName === "write" || toolName === "edit") {
    const filePath = String(params.path || params.file_path || "");
    for (const pattern of EXEMPT_PATH_PATTERNS) {
      if (pattern.test(filePath)) return null;
    }
  }

  // Check for active task registration
  const task = getActiveTask();
  if (task) return null; // task registered, allow

  // Block: no active task registered
  return {
    decision: "block",
    reason:
      "TASK TRACKING GATE: No active task registered.\n\n" +
      "Before doing work, you MUST register what you're working on:\n\n" +
      "```\n" +
      "Write to .active-task.json:\n" +
      "{\n" +
      '  "name": "Brief task description",\n' +
      '  "source": "trello|manual",\n' +
      '  "taskId": "trello-card-id (if applicable)",\n' +
      '  "url": "trello card url (if applicable)",\n' +
      '  "registered": ' + Date.now() + "\n" +
      "}\n" +
      "```\n\n" +
      "This ensures every work session is tracked and survives compaction.\n" +
      "Register your task, then retry.",
  };
};
