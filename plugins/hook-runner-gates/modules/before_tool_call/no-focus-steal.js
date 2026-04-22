// TOOLS: Bash
// WHY: Background process launches opened visible terminal tabs that stole focus.
// Only applies on Windows where child_process.spawn flashes a console.

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  if (process.platform !== "win32") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");

  const fileOpenPattern = /\bstart\s+(""|'')\s+["']?[^"']*\.(pdf|html?|png|jpe?g|gif|txt|md|csv|xlsx?|docx?|pptx?)\b/i;
  if (fileOpenPattern.test(cmd)) return null;

  const hasTrailingAmpersand = /[^&]&\s*$/.test(cmd);
  const hasNohup = /\bnohup\b/.test(cmd);
  const hasStartExe = /\bstart\s+(""|'')\s+["']?\w+\.(exe|bat|cmd|ps1)\b/i.test(cmd) ||
    /\bstart\s+(""|'')\s+(cmd|powershell|python|node|bash|claude)\b/i.test(cmd);

  if (!hasTrailingAmpersand && !hasNohup && !hasStartExe) return null;

  const spawnsProcess = /\b(node|python|bash|claude|powershell)\b/.test(cmd);
  if (!spawnsProcess && !hasStartExe) return null;

  return {
    decision: "block",
    reason:
      "FOCUS STEAL: This spawns a background process that flashes a " +
      "console window on Windows. Use run_in_background parameter instead, " +
      "or for long-running daemons use a scheduled task with hidden window.\n" +
      'If opening a file, use: start "" "path/to/file.ext"',
  };
};
