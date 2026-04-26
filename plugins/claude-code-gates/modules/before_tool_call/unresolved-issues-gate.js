// TOOLS: Bash
// WHY: Claude commits code while TODO.md still has unresolved FAIL, timeout,
// MISMATCH, or WARN entries. Bugs ship because the commit focused on what worked.

const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const { extractCommitMsg } = require("../../_helpers.js");

const ISSUE_PATTERNS = [
  /\bFAIL\b/,
  /\btimeout\b/i,
  /\bMISMATCH\b/,
  /\bWARN(?:ING)?\b/,
  /\bERROR\b/,
  /\bBROKEN\b/i,
  /\bcrash(?:ed|es|ing)?\b/i,
];

const FALSE_POSITIVE_PATTERNS = [
  /- \[x\].*\bFAIL/i,
  /\bfix(?:ed|es|ing)?\b.*\bFAIL/i,
  /\b0\s+fail/i,
  /\b0\s+FAIL/,
  /passed,\s*0\s+failed/i,
  /\bno\s+fail/i,
  /FAIL\/WARN/,
];

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!/git\s+commit/.test(cmd)) return null;

  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const todoPath = join(projectDir, "TODO.md");

  if (!existsSync(todoPath)) return null;

  let content = "";
  try { content = readFileSync(todoPath, "utf-8"); } catch { return null; }

  const lines = content.split("\n");
  const issues = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/- \[x\]/.test(line)) continue;

    let isFP = false;
    for (const fp of FALSE_POSITIVE_PATTERNS) {
      if (fp.test(line)) { isFP = true; break; }
    }
    if (isFP) continue;

    for (const pattern of ISSUE_PATTERNS) {
      if (pattern.test(line)) {
        if (/^\s*-\s*\[ \]/.test(line) || /Status:|TESTING|IN PROGRESS/i.test(line)) {
          issues.push(`  L${i + 1}: ${line.trim().substring(0, 120)}`);
          break;
        }
      }
    }
  }

  if (issues.length === 0) return null;

  const msg = extractCommitMsg(cmd);
  if (msg && /\b(known|pre-existing|intermittent|expected|acknowledged|wontfix)\b/i.test(msg)) {
    return null;
  }

  return {
    decision: "block",
    reason:
      `UNRESOLVED ISSUES in TODO.md (${issues.length} found):\n\n` +
      issues.slice(0, 8).join("\n") +
      (issues.length > 8 ? `\n  ... and ${issues.length - 8} more` : "") +
      "\n\nBefore committing:\n" +
      "  1. Address each issue (fix it, file a plan, or mark as known)\n" +
      "  2. Update TODO.md with the resolution\n" +
      "  3. Or add 'known'/'pre-existing'/'intermittent' to commit message to acknowledge",
  };
};
