// TOOLS: Write, Edit
// WHY: On Windows, Write/Edit can produce CRLF line endings that break shell
// scripts, YAML files, and other Unix-sensitive formats.

const { readFileSync } = require("node:fs");
const { basename, extname } = require("node:path");

const SENSITIVE_EXTENSIONS = [".sh", ".bash", ".yml", ".yaml", ".py", ".rb", ".pl", ".env", ".conf", ".cfg"];

module.exports = function(input) {
  const toolName = input.tool_name;
  if (toolName !== "Write" && toolName !== "Edit") return null;
  const params = input.tool_input || {};

  const filePath = String(params.file_path || "");
  if (!filePath) return null;

  const ext = extname(filePath).toLowerCase();
  if (!SENSITIVE_EXTENSIONS.includes(ext)) return null;

  let content;
  try { content = readFileSync(filePath, "utf-8"); } catch { return null; }
  if (!content.includes("\r\n")) return null;

  let crlfCount = 0;
  for (let i = 0; i < content.length - 1; i++) {
    if (content[i] === "\r" && content[i + 1] === "\n") crlfCount++;
  }

  return {
    message:
      `WARNING: ${basename(filePath)} has ${crlfCount} CRLF line endings. ` +
      "Shell scripts, YAML, and Python files break with \\r\\n on Unix. " +
      `Fix with: sed -i 's/\\r$//' ${filePath}`,
  };
};
