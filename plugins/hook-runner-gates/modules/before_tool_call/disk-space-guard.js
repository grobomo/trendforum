// TOOLS: Bash
// WHY: Claude ran rm -rf on temp files when disk was full without asking.
// Blocks destructive commands when a previous error was disk-related.

const { existsSync } = require("node:fs");
const { join } = require("node:path");
const { homedir } = require("node:os");

const DISK_SPACE_STATE_FILE = join(homedir(), ".claude", ".disk-space-alert");

const DISK_DESTRUCTIVE_PATTERNS = [
  /\brm\s+-rf?\b/,
  /\brm\s+.*-[a-z]*f/,
  /\brmdir\b/,
  /\bdel\b.*\/[sS]/,
  /Remove-Item.*-Recurse/i,
  /\bclean\b.*--force/,
  /\bprune\b/,
  /\bpurge\b/,
];

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!cmd) return null;

  let inAlert = false;
  try { inAlert = existsSync(DISK_SPACE_STATE_FILE); } catch { /* ignore */ }
  if (!inAlert) return null;

  for (const pattern of DISK_DESTRUCTIVE_PATTERNS) {
    if (pattern.test(cmd)) {
      return {
        decision: "block",
        reason:
          "DISK SPACE GUARD: Destructive command blocked during disk space emergency.\n" +
          "WHY: Deleting files to free space risks destroying important data.\n" +
          "Run a disk usage scan first to identify safe cleanup candidates.\n" +
          "Present the results and wait for explicit user approval.\n" +
          "Command blocked: " + cmd.substring(0, 100),
      };
    }
  }

  return null;
};
