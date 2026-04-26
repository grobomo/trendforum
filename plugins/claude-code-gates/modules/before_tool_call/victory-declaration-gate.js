// TOOLS: Bash
// WHY: Claude declares victory prematurely — "all tests pass" in commit messages
// when failures were skipped, warnings ignored, or outputs not reviewed.

const { extractCommitMsg } = require("../../_helpers.js");

const VICTORY_WORDS = /\b(all\s+(tests?\s+)?pass(ed|ing|es)?|all\s+green|succeeded|fully\s+working|complete[ds]?\s+(successfully)?|100%|zero\s+fail)/i;

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!/git\s+commit/.test(cmd)) return null;

  const msg = extractCommitMsg(cmd);
  if (!msg) return null;

  const title = msg.split("\n")[0];
  if (!VICTORY_WORDS.test(title)) return null;

  return {
    decision: "block",
    reason:
      "VICTORY DECLARATION in commit message.\n\n" +
      `Your message claims success: "${msg.substring(0, 120)}"\n\n` +
      "Before committing, verify:\n" +
      "  1. Did you review EVERY failure, warning, and timeout in the output?\n" +
      "  2. Did you check for empty/missing outputs that should have content?\n" +
      "  3. Did you look at what's NOT in the results that should be?\n" +
      "  4. Are there unresolved FAIL/WARN/MISMATCH in TODO.md?\n\n" +
      "Rephrase with specifics:\n" +
      '  BAD:  "All tests pass"\n' +
      '  GOOD: "T442: Fix testbox gate — 17/17 tests pass, synced to live"\n\n' +
      "Include the count, the scope, and what was tested.",
  };
};
