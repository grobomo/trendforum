// WHY: Companion to disk-space-guard. Detects disk space errors in output
// and sets alert mode so destructive commands are blocked.

const { existsSync, writeFileSync, unlinkSync } = require("node:fs");
const { join } = require("node:path");
const { homedir } = require("node:os");

const DISK_SPACE_STATE_FILE = join(homedir(), ".claude", ".disk-space-alert");

const DISK_ERROR_PATTERNS = [
  /out of diskspace/i,
  /no space left on device/i,
  /not enough space/i,
  /disk is full/i,
  /write error.*diskspace/i,
  /ENOSPC/,
];

module.exports = function(input) {
  const output = input.result || "";

  for (const pattern of DISK_ERROR_PATTERNS) {
    if (pattern.test(output)) {
      try {
        writeFileSync(DISK_SPACE_STATE_FILE, new Date().toISOString() + "\n" + output.substring(0, 500));
      } catch { /* disk may be full */ }

      return {
        message:
          "DISK SPACE ALERT: The last command failed due to insufficient disk space.\n" +
          "DO NOT attempt to delete files to free space.\n" +
          "Run a disk usage scan to identify safe cleanup candidates.\n" +
          "Present the results to the user and WAIT for explicit approval.\n" +
          "To clear this alert after resolving: delete ~/.claude/.disk-space-alert",
      };
    }
  }

  try {
    if (existsSync(DISK_SPACE_STATE_FILE)) {
      const hasError = /error|fail|fatal/i.test(output) && /disk|space|write/i.test(output);
      if (!hasError) {
        unlinkSync(DISK_SPACE_STATE_FILE);
      }
    }
  } catch { /* ignore */ }

  return null;
};
