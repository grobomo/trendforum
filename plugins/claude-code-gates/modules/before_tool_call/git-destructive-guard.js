// TOOLS: Bash
// WHY: Claude ran `git reset --hard` and `git checkout .` to "clean up" working
// trees, destroying uncommitted work. These ops are rarely the right solution.

const { stripQuotedContent } = require("../../_helpers.js");

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const fullCmd = String(params.command || "");
  const cmd = stripQuotedContent(fullCmd);

  if (/git\s+reset\s+--hard/.test(cmd)) {
    return {
      decision: "block",
      reason:
        "DESTRUCTIVE: git reset --hard destroys uncommitted changes permanently.\n" +
        "Alternatives:\n" +
        "  git stash        — save changes for later\n" +
        "  git reset --soft — move HEAD but keep changes staged\n" +
        "  git checkout <file> — revert specific files only\n" +
        "If you truly need --hard, ask the user first.",
    };
  }

  const checkoutMatch = cmd.match(/git\s+(checkout|restore)\s+(.*)/);
  if (checkoutMatch) {
    const subcmd = checkoutMatch[1];
    const args = checkoutMatch[2].split(/\s*(?:&&|\|\||\||;|[12]?>>?)\s*/)[0].trim();
    if (subcmd === "checkout" && /^(-b|--orphan|-t|--track|-)\s/.test(args)) return null;
    if (subcmd === "checkout" && args && !/[.\/\\]/.test(args) && !/^--\s/.test(args)) return null;
    return {
      decision: "block",
      reason:
        `DESTRUCTIVE: \`git ${subcmd} ${args}\` discards uncommitted changes.\n` +
        "Alternatives:\n" +
        "  git stash                — save changes for later\n" +
        "  git diff <file>          — review changes first\n" +
        "If you truly need to discard changes, ask the user first.",
    };
  }

  if (/git\s+clean\s+-[a-z]*f/.test(cmd)) {
    return {
      decision: "block",
      reason:
        "DESTRUCTIVE: git clean -f permanently deletes untracked files.\n" +
        "Run git clean -n first to preview what would be deleted.\n" +
        "If you truly need to clean, ask the user first.",
    };
  }

  return null;
};
