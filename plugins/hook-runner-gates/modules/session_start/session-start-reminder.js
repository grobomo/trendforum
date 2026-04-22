// WHY: Important operational context was missing at session start.
// Inject working instructions at start of every session.

const SESSION_START_TEXT =
  "SESSION START INSTRUCTIONS: Check TODO.md in the workspace for pending tasks. " +
  "If tasks remain, do the next one. Review recent conversation history for incomplete " +
  "tangents from previous sessions. Organize, optimize, secure the project. Then zoom out " +
  "and expand. Always write plans to TODO.md before executing. Save state to TODO.md before " +
  "context resets.\n\n" +
  "IMPORTANT: If TODO.md has a session handoff from a previous session, read it FIRST — " +
  "it tells you what was done and what matters next. Mindset: be slow and systematic. " +
  "Build repeatable, modular code with excellent user experience. No rush.";

module.exports = function(_input) {
  return { text: SESSION_START_TEXT };
};
