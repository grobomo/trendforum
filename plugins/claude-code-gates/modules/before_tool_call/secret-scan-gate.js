// TOOLS: Bash
// WHY: API keys were committed to git history and had to be rotated.

const { execFileSync } = require("node:child_process");
const { SECRET_PATTERNS } = require("../../_helpers.js");

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!/^\s*git\s+commit/.test(cmd) && !/&&\s*git\s+commit/.test(cmd)) return null;

  let diff = "";
  try {
    diff = execFileSync("git", ["diff", "--cached", "--diff-filter=ACMR"], {
      encoding: "utf-8",
      timeout: 10000,
      maxBuffer: 1024 * 1024,
    });
  } catch {
    return null;
  }

  if (!diff) return null;

  const addedLines = diff.split("\n").filter((line) =>
    line.charAt(0) === "+" && !line.startsWith("+++")
  );

  const filteredLines = addedLines.filter((line) => {
    if (/os\.environ|process\.env|getenv|secretsmanager|get-secret-value|credential/i.test(line)) return false;
    if (/[:=]\s*["']?\s*["']?\s*$/.test(line)) return false;
    if (/\$\{?\w*TOKEN\w*[:\-}]/.test(line)) return false;
    if (/\$\{?\w*SECRET\w*[:\-}]/.test(line)) return false;
    return true;
  });
  const filteredText = filteredLines.join("\n");

  const findings = [];
  for (const pat of SECRET_PATTERNS) {
    if (filteredLines.some((line) => pat.re.test(line))) {
      if (pat.context && !pat.context.test(filteredText)) continue;
      findings.push(pat.name);
    }
  }

  if (findings.length > 0) {
    return {
      decision: "block",
      reason:
        "SECRET SCAN: Potential secrets detected in staged changes:\n" +
        findings.map((f) => "  - " + f).join("\n") +
        "\nReview with: git diff --cached\n" +
        "Use environment variables or credential-manager instead of hardcoded secrets.",
    };
  }

  return null;
};
