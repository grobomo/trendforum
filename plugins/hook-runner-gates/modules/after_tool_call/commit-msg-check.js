// TOOLS: Bash
// WHY: Sloppy commit messages made PR history unreadable.

const { extractCommitMsg } = require("../../_helpers.js");

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const command = String(params.command || "");
  if (!/\bgit\s+commit\b/.test(command)) return null;
  if (/--amend/.test(command)) return null;

  const msg = extractCommitMsg(command);
  if (!msg) return null;

  const firstLine = msg.split("\n")[0];
  const warnings = [];

  if (/^(wip|fixup!|squash!|tmp|temp)\b/i.test(firstLine)) {
    warnings.push(`Commit message starts with '${firstLine.split(/\s/)[0]}' — not suitable for final commits`);
  }

  if (firstLine.length > 72) {
    warnings.push(`First line is ${firstLine.length} chars (convention: max 72)`);
  }

  if (warnings.length > 0) {
    return { message: "Commit message issues:\n" + warnings.map((w) => "- " + w).join("\n") };
  }

  return null;
};
