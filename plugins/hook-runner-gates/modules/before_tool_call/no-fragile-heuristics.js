// TOOLS: Edit, Write
// WHY: Claude wrote pixel-ratio thresholds and color-counting heuristics to
// detect blank screenshots. These broke on edge cases. Use LLM analysis instead.

const { basename } = require("node:path");

const FRAGILE_PATTERNS = [
  /pixel.*ratio|ratio.*pixel/i,
  /white_ratio|white_ish|white_percent/i,
  /unique_color|color_count|color_divers/i,
  /getpixel|getdata\(\)|\.convert\(.*RGB/i,
  /threshold.*0\.\d+.*blank|blank.*threshold/i,
  /quantize.*color|color.*quantize/i,
];

module.exports = function(input) {
  const toolName = input.tool_name;
  if (toolName !== "Edit" && toolName !== "Write") return null;
  const params = input.tool_input || {};

  const content = toolName === "Edit"
    ? String(params.new_string || "")
    : String(params.content || "");

  const filePath = String(params.file_path || "");

  if (!/review|verify|check|quality|validate|analyz/i.test(filePath)) return null;

  for (const pattern of FRAGILE_PATTERNS) {
    if (pattern.test(content)) {
      return {
        decision: "block",
        reason:
          `FRAGILE HEURISTIC DETECTED in ${basename(filePath)}: ` +
          "You're writing pixel/color threshold code for visual judgment. " +
          "This is fragile and will break on edge cases. " +
          "Use an LLM API to analyze images/PDFs instead. " +
          "Describe the check in plain English as a prompt, send the artifact, parse structured output.",
      };
    }
  }

  return null;
};
