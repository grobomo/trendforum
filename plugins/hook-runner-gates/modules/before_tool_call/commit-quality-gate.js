// TOOLS: Bash
// WHY: Generic commit messages like "fix" or "update" make git history useless.

const { extractCommitMsg } = require("../../_helpers.js");

const GENERIC_STARTS = /^\s*(fix|update|change|modify|edit|tweak|adjust|minor|wip|tmp|temp|stuff|misc|cleanup)\b/i;
const MIN_WORDS = 5;

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!/git\s+commit/.test(cmd)) return null;
  if (/--amend/.test(cmd)) return null;

  const msg = extractCommitMsg(cmd);
  if (!msg) return null;

  const words = msg.split(/\s+/).filter((w) => w.length > 0);

  if (words.length < MIN_WORDS) {
    return {
      decision: "block",
      reason:
        `COMMIT MESSAGE TOO SHORT: ${words.length} words (min ${MIN_WORDS}).\n` +
        `Your message: "${msg}"\n` +
        'Good format: "Fix <what> — <why>" or "Add <feature> for <purpose>"',
    };
  }

  if (GENERIC_STARTS.test(msg) && words.length < 8) {
    return {
      decision: "block",
      reason:
        `COMMIT MESSAGE TOO GENERIC: starts with '${words[0]}' without enough detail.\n` +
        `Your message: "${msg}"\n` +
        'Say WHAT changed and WHY. Example: "Fix spec-gate cache — stale hasUnchecked when tasks.md edited"',
    };
  }

  return null;
};
