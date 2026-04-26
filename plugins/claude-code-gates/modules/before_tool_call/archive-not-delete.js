// TOOLS: Bash
// WHY: Claude deleted files that turned out to be needed later.
// Block destructive delete commands. Always archive, never delete.

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");

  const stripped = cmd
    .replace(/\$\(cat <<'EOF'[\s\S]*?EOF\s*\)/g, "MSG")
    .replace(/\$\(cat <<EOF[\s\S]*?EOF\s*\)/g, "MSG")
    .replace(/"(?:[^"\\]|\\.)*"/g, "STR")
    .replace(/'(?:[^'\\]|\\.)*'/g, "STR");

  const normalized = stripped.replace(/\s+/g, " ").trim();

  const destructive = [
    /\brm\s+-rf\b/,
    /\brm\s+-fr\b/,
    /\brm\s+-r\b/,
    /\brm\s+--recursive\b/,
    /\brm\b(?!.*\.log\b)(?!.*\.tmp\b)(?!.*node_modules\b)(?!.*__pycache__\b)(?!.*\.pyc\b)/,
    /\brmdir\b/,
    /\bdel\s+\/[sS]\b/i,
    /\brd\s+\/[sS]\b/i,
  ];

  const exceptions = [
    /node_modules/,
    /\.pyc$/,
    /__pycache__/,
    /\.log$/,
    /\.tmp$/,
    /\.cache/,
    /\/tmp\//,
    /\btmp\b.*\brm\b/,
    /dist\//,
    /build\//,
    /\bgit\s+rm\s+(-r\s+)?--cached\b/,
    /\bgit\s+rm\s+--cached\b/,
    /\.git\/.*\.lock\b/,
  ];

  for (const pattern of destructive) {
    if (pattern.test(normalized)) {
      for (const exception of exceptions) {
        if (exception.test(normalized)) return null;
      }
      return {
        decision: "block",
        reason:
          "BLOCKED: Destructive delete detected. NEVER delete files or directories. " +
          "Move to archive/ instead. Use: mv <path> archive/ (create archive/ if needed, " +
          "add to .gitignore). Command was: " + cmd.substring(0, 200),
      };
    }
  }

  return null;
};
