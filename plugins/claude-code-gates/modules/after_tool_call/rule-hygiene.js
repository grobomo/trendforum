// WHY: Rules grew into multi-topic dump files that were hard to maintain.

const { existsSync, readFileSync } = require("node:fs");
const { basename } = require("node:path");

module.exports = function(input) {
  const params = input.tool_input || {};
  const filePath = String(params.file_path || "");
  const normalized = filePath.replace(/\\/g, "/");

  if (!normalized.includes("/rules/") || !normalized.endsWith(".md")) return null;

  const warnings = [];
  const fileName = basename(normalized, ".md");

  const badNames = ["session-", "gotchas", "misc", "notes", "todo", "temp"];
  for (const bad of badNames) {
    if (fileName.toLowerCase().startsWith(bad) || fileName.toLowerCase() === bad) {
      warnings.push(`Bad rule filename "${fileName}.md" - use a descriptive topic name`);
      break;
    }
  }

  if (existsSync(filePath)) {
    const content = readFileSync(filePath, "utf8");
    const lines = content.split("\n");

    if (lines.length > 25) {
      warnings.push(`Rule file is ${lines.length} lines - keep under 20. Split into multiple files.`);
    }

    let h2Count = 0;
    for (const line of lines) {
      if (line.startsWith("## ")) h2Count++;
    }
    if (h2Count > 2) {
      warnings.push(`Rule file has ${h2Count} sections - likely covers multiple topics. One topic per file.`);
    }
  }

  const home = (process.env.HOME || "").replace(/\\/g, "/");
  if (home && normalized.includes(home + "/.claude/rules/")) {
    const projectKeywords = ["dispatcher", "bootstrap", "worker", "rone", "teams", "poller"];
    for (const kw of projectKeywords) {
      if (fileName.toLowerCase().includes(kw)) {
        warnings.push(`"${fileName}.md" looks project-specific but is in global rules. Move to project .claude/rules/`);
        break;
      }
    }
  }

  if (warnings.length === 0) return null;
  return { message: "Rule hygiene:\n" + warnings.map((w) => "- " + w).join("\n") };
};
