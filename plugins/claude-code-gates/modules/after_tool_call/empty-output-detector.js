// TOOLS: Bash
// WHY: Claude treats empty command output as success — e.g., `ls screenshots/`
// returning nothing means no screenshots exist, but Claude proceeds as if they do.

const EXPECT_OUTPUT = [
  /^\s*ls\b/,
  /^\s*find\b/,
  /^\s*cat\b/,
  /^\s*node\s+.*--test/,
  /^\s*node\s+setup\.js\s+--/,
  /^\s*curl\b/,
  /^\s*az\s/,
  /^\s*kubectl\s+(get|describe|logs)\b/,
];

const EMPTY_OK = [
  /^\s*(cp|mv|mkdir|rm|chmod|touch|cd)\b/,
  /^\s*git\s+(add|checkout|push|pull|fetch|merge)\b/,
  />/,
  /2>&1\s*$/,
  /\|\s*wc\b/,
];

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  const output = (input.result || "").trim();
  if (output.length > 0) return null;

  for (const pattern of EMPTY_OK) {
    if (pattern.test(cmd)) return null;
  }

  let expectsOutput = false;
  for (const pattern of EXPECT_OUTPUT) {
    if (pattern.test(cmd)) { expectsOutput = true; break; }
  }
  if (!expectsOutput) return null;

  return {
    message:
      "EMPTY OUTPUT from command that normally produces output.\n\n" +
      "Command: " + cmd.substring(0, 150) + "\n\n" +
      "This likely means:\n" +
      "  - Directory is empty (no files where expected)\n" +
      "  - File doesn't exist at that path\n" +
      "  - Query returned no results\n" +
      "  - Command failed silently\n\n" +
      "Investigate before proceeding. Do not assume empty = success.",
  };
};
