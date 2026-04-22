// TOOLS: Bash
// WHY: Claude masked bugs with cleanup instead of fixing root causes.

const CLEANUP_PATTERNS = [
  /git reset --hard/,
  /git checkout -- \.$/,
  /rm -rf.*requests\//,
  /mv.*requests\/failed/,
  /mv.*requests\/dispatched.*archived/,
];

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");

  for (const pattern of CLEANUP_PATTERNS) {
    if (pattern.test(cmd)) {
      return {
        decision: "block",
        reason:
          "Root cause first: you're about to clean up a symptom. " +
          "Before running this, diagnose WHY it happened and fix the root cause. " +
          "What caused the dirty state / conflict / failure? Fix that first, then clean up.",
      };
    }
  }

  return null;
};
