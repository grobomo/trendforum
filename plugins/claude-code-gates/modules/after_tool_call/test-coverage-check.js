// TOOLS: Edit, Write
// WHY: Source files were modified but existing tests never ran, hiding regressions.

const { existsSync, readdirSync } = require("node:fs");
const { basename, dirname, extname, join, relative } = require("node:path");

const TEST_DIRS = ["scripts/test", "test", "tests", "__tests__", "spec"];
const TEST_PREFIXES = ["test-", "test_"];
const TEST_SUFFIXES = [".test.js", ".test.ts", ".spec.js", ".spec.ts", "_test.go", "_test.py"];

module.exports = function(input) {
  const toolName = input.tool_name;
  if (toolName !== "Edit" && toolName !== "Write") return null;
  const params = input.tool_input || {};

  const filePath = String(params.file_path || "");
  if (!filePath) return null;

  const base = basename(filePath);
  const dir = dirname(filePath);

  for (const prefix of TEST_PREFIXES) {
    if (base.startsWith(prefix)) return null;
  }
  for (const suffix of TEST_SUFFIXES) {
    if (base.endsWith(suffix)) return null;
  }
  const normPath = filePath.replace(/\\/g, "/");
  for (const td of TEST_DIRS) {
    if (normPath.includes(`/${td}/`)) return null;
  }

  const codeExts = [".js", ".ts", ".py", ".go", ".rs", ".java", ".sh", ".bash"];
  if (!codeExts.includes(extname(base).toLowerCase())) return null;

  const projectDir = process.env.CLAUDE_PROJECT_DIR || dir;
  const nameNoExt = base.replace(/\.[^.]+$/, "");
  const found = [];

  for (const td of TEST_DIRS) {
    const testDir = join(projectDir, td);
    if (!existsSync(testDir)) continue;
    let files;
    try { files = readdirSync(testDir); } catch { continue; }
    for (const f of files) {
      if (f.toLowerCase().includes(nameNoExt.toLowerCase())) {
        found.push(join(td, f));
      }
    }
  }

  try {
    for (const sib of readdirSync(dir)) {
      if (sib === base) continue;
      const sibLower = sib.toLowerCase();
      const nameCheck = nameNoExt.toLowerCase();
      if (sibLower.startsWith("test-" + nameCheck) ||
        sibLower.startsWith("test_" + nameCheck) ||
        sibLower === nameCheck + ".test.js" ||
        sibLower === nameCheck + ".test.ts" ||
        sibLower === nameCheck + ".spec.js" ||
        sibLower === nameCheck + ".spec.ts") {
        found.push(join(relative(projectDir, dir) || ".", sib));
      }
    }
  } catch { /* ignore */ }

  if (found.length === 0) return null;

  const unique = [...new Set(found)];
  return { message: `Modified ${base} — related test file(s) found: ${unique.join(", ")}. Run tests before committing.` };
};
