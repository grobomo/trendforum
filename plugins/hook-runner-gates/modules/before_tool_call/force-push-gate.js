// TOOLS: Bash
// WHY: Force-pushing to main/master can destroy shared history and others' work.

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "").replace(/\s+/g, " ").trim();
  if (!/\bgit\s+push\b/.test(cmd)) return null;

  const hasForce = /\s--force\b/.test(cmd) || /\s-f\b/.test(cmd) || /\s--force-with-lease\b/.test(cmd);
  if (!hasForce) return null;

  for (const branch of ["main", "master"]) {
    if (new RegExp("\\b" + branch + "\\b").test(cmd)) {
      return {
        decision: "block",
        reason: `BLOCKED: Force-push to ${branch} is destructive and irreversible. Use a regular push or create a revert commit instead.`,
      };
    }
  }

  return null;
};
