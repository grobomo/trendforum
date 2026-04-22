// TOOLS: Write, Edit
// WHY: Hardcoded absolute user paths in scripts broke portability across machines.

const { basename } = require("node:path");

module.exports = function(input) {
  const toolName = input.tool_name;
  if (toolName !== "Write" && toolName !== "Edit") return null;
  const params = input.tool_input || {};

  const text = toolName === "Write"
    ? String(params.content || "")
    : String(params.new_string || "");

  if (!text) return null;

  const filePath = String(params.file_path || "");
  const ext = filePath.split(".").pop()?.toLowerCase() || "";
  if (["md", "txt", "html"].includes(ext)) return null;
  if (/cloudformation[\\\/]/i.test(filePath) && ["yaml", "yml"].includes(ext)) return null;
  if (/Dockerfile/i.test(basename(filePath))) return null;

  const winPath = /[A-Z]:[\\\/]Users[\\\/]\w+[\\\/]/i;
  const linuxPath = /\/home\/\w+\//;
  const macPath = /\/Users\/\w+\//;

  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (/^(\/\/|#|\/\*|\*|<!--)/.test(trimmed)) continue;
    if (/["'].*example.*["']/i.test(trimmed)) continue;

    let match = null;
    if (winPath.test(trimmed)) match = trimmed.match(winPath);
    else if (linuxPath.test(trimmed)) match = trimmed.match(linuxPath);
    else if (macPath.test(trimmed)) match = trimmed.match(macPath);

    if (match) {
      return {
        decision: "block",
        reason:
          `HARDCODED PATH DETECTED in ${toolName} content.\n` +
          `Found: ${match[0]}\n` +
          "Use a variable (HOME, __dirname, process.cwd()) or relative path instead.\n" +
          "Hardcoded absolute paths break portability across machines.",
      };
    }
  }

  return null;
};
