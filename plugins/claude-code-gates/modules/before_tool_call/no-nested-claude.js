// TOOLS: Bash
// WHY: Nested `claude -p` calls inside a session don't work reliably.
// Cross-project work must use a proper new terminal session.

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");

  const isSearchPattern = /\b(grep|rg|findstr|awk|sed)\b/.test(cmd) &&
                          /["'].*claude.*["']/.test(cmd);
  if (isSearchPattern) return null;

  if (/\b(git\s+(commit|push|pull|fetch|log|diff|status|add|tag|branch|merge|rebase|stash|show|remote|config|checkout))\b/.test(cmd)) return null;
  if (/\bgh\s/.test(cmd)) return null;

  if (/\bclaude\s+(-p|--print|-m|--message)\b/.test(cmd) ||
      /\|\s*claude\b/.test(cmd) ||
      /\bclaude\s+-/.test(cmd)) {
    return {
      decision: "block",
      reason:
        "NO NESTED CLAUDE: Cannot run claude as a subprocess — it doesn't work reliably.\n" +
        "FIX: Open a new terminal tab and run claude there, or use a proper session spawner.",
    };
  }

  return null;
};
