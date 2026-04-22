// TOOLS: Bash
// WHY: Claude adds sleep between actions thinking pages or processes need
// time to load. Each prompt takes 3-10s — more than enough. Sleep wastes time.

module.exports = function(input) {
  if (input.tool_name !== "Bash") return null;
  const params = input.tool_input || {};

  const cmd = String(params.command || "");
  if (!/^\s*sleep\b/.test(cmd)) return null;

  const seconds = cmd.match(/sleep\s+(\d+)/);
  if (!seconds) return null;
  const dur = parseInt(seconds[1], 10);

  if (dur <= 1) return null;

  return {
    decision: "block",
    reason:
      "PERFORMANCE: Do not use sleep between actions.\n" +
      "Each prompt takes 3-10s to process — more than enough for pages to load.\n" +
      "Just call the next action directly. Sleep wastes time twice.\n" +
      "If you truly need a delay, use sleep 1 (max 1 second).",
  };
};
