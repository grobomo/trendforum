// TOOLS: Bash
// WHY: Claude tried 3 wrong ways before finding the right pattern. This
// detects "fail-fail-succeed" cycles and prompts to create a hook module
// so the solution is enforced permanently.

const state = {
  failures: [],
  lastPrompted: 0,
};

const FAIL_THRESHOLD = 2;

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  const output = input.result || "";

  let exitCode = -1;
  const exitMatch = output.match(/Exit code (\d+)/);
  if (exitMatch) {
    exitCode = parseInt(exitMatch[1], 10);
  } else if (!output.includes("Exit code") && !output.includes("error")) {
    exitCode = 0;
  }

  if (exitCode !== 0) {
    state.failures.push({ ts: Date.now(), cmd: cmd.substring(0, 200) });
    const cutoff = Date.now() - 300000;
    state.failures = state.failures.filter(f => f.ts > cutoff);
    return null;
  }

  const recentFailures = state.failures.length;
  if (recentFailures < FAIL_THRESHOLD) {
    state.failures = [];
    return null;
  }

  if (Date.now() - state.lastPrompted < 300000) {
    state.failures = [];
    return null;
  }

  const failedCmds = state.failures.map(f => f.cmd).join("\n  ");
  state.failures = [];
  state.lastPrompted = Date.now();

  return {
    message:
      "TROUBLESHOOTING CYCLE DETECTED: " + recentFailures + " failed attempts before success.\n" +
      "Failed commands:\n  " + failedCmds + "\n" +
      "Successful command: " + cmd.substring(0, 200) + "\n\n" +
      "You just learned something the hard way. To prevent repeating this:\n" +
      "1) Create a hook module that catches the bad pattern and suggests the good one\n" +
      "2) Commit it so it persists across sessions\n" +
      "3) If this pattern exists in another project, you should have checked there FIRST\n\n" +
      "Do this NOW before moving on.",
  };
};
