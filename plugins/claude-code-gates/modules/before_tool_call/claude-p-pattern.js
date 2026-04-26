// TOOLS: Bash, Edit, Write
// WHY: Claude tried 3 wrong ways to call claude -p before finding the right
// pattern. The correct pattern is: write to temp file, pipe via stdin redirect.

const CLAUDE_P_CORRECT =
  "\n\nCorrect claude -p pattern:\n" +
  "  PROMPTFILE=$(mktemp /tmp/claude-p-XXXXXX.txt)\n" +
  "  cat > \"$PROMPTFILE\" <<'EOF'\n  Your prompt here\n  EOF\n" +
  "  claude -p --dangerously-skip-permissions < \"$PROMPTFILE\" > output.txt 2>&1\n" +
  "  rm -f \"$PROMPTFILE\"\n\n" +
  "For images/PDFs: put absolute file paths in the prompt and tell Claude\n" +
  "to use the Read tool to view them. NEVER base64-encode images inline.\n" +
  "No API key needed. No SDK needed. Same auth as Claude Code session.";

module.exports = function(input) {
  const toolName = input.tool_name;
  const params = input.tool_input || {};

  if (toolName === "Bash") {
    const cmd = String(params.command || "");
    if (cmd.indexOf("claude -p") === -1 && cmd.indexOf("claude.exe -p") === -1) return null;

    const bad = [];
    if (/claude\s+-p\s+--no-input/.test(cmd)) bad.push("--no-input is not a valid flag");
    if (/echo\s+.*\|\s*claude\s+-p/.test(cmd)) bad.push("piping via echo hangs — use temp file + stdin redirect");
    if (/claude\s+-p\s+"[^"]+"\s*2?>&?1?$/.test(cmd)) bad.push("passing prompt as argument is unreliable");

    if (bad.length > 0) {
      return {
        decision: "block",
        reason: "claude -p invocation issue: " + bad.join("; ") + CLAUDE_P_CORRECT,
      };
    }
    return null;
  }

  if (toolName !== "Edit" && toolName !== "Write") return null;

  const content = toolName === "Edit"
    ? String(params.new_string || "")
    : String(params.content || "");

  if (!/claude.*-p|anthropic|ANTHROPIC_API_KEY/i.test(content)) return null;

  const filePath = String(params.file_path || "");
  if (/claude-p-pattern|run-modules/i.test(filePath)) return null;
  if (/claude.api|anthropic.sdk|api.wrapper/i.test(filePath)) return null;

  if (/ANTHROPIC_API_KEY|os\.environ.*anthropic|api_key.*=.*os\./i.test(content)) {
    if (/not.*need|no.*key.*needed|same.*auth/i.test(content)) return null;
    return {
      decision: "block",
      reason: "Don't check for ANTHROPIC_API_KEY. claude -p uses Claude Code's " +
        "own auth — no API key needed." + CLAUDE_P_CORRECT,
    };
  }

  if (/base64.*encode.*image|b64encode.*read|base64\.b64encode.*\.png/i.test(content)) {
    return {
      decision: "block",
      reason: "Don't base64-encode images into claude -p prompts. They're too " +
        "large and cause timeouts. Include absolute file paths in the prompt " +
        "and tell Claude to use its Read tool to view them." + CLAUDE_P_CORRECT,
    };
  }

  if (/import anthropic|from anthropic import|anthropic\.Anthropic/i.test(content)) {
    return {
      decision: "block",
      reason: "Don't use the Anthropic SDK when claude -p is available. " +
        "claude -p is simpler (no API key, no SDK install)." + CLAUDE_P_CORRECT,
    };
  }

  return null;
};
