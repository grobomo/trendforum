// WHY: Claude stops and lists options instead of doing the work.
// The message text in stop-message.txt was iterated over 15+ versions by the user.
// DO NOT rewrite, condense, or rephrase it. It is a user-authored artifact.
// If you need to change behavior, modify THIS CODE, not the message file.

const { readFileSync } = require("node:fs");
const path = require("node:path");

let _stopMessage = null;
function getStopMessage() {
  if (!_stopMessage) {
    try {
      _stopMessage = readFileSync(path.join(__dirname, "..", "..", "stop-message.txt"), "utf-8").trim();
    } catch {
      _stopMessage = "DO NOT STOP. Check TODO.md for pending tasks and do the next one.";
    }
  }
  return _stopMessage;
}

const LAZY_STOP_PATTERNS = [
  /\bwant me to\b/i,
  /\bwould you like me to\b/i,
  /\bshould i\b/i,
  /\blet me know if you(?:'d)? (?:like|want|prefer)\b/i,
  /\bhere are (?:some |your |the )?options\b/i,
  /\bhere(?:'s| is) what (?:i |we )?(?:can|could) do\b/i,
  /\bdo you want me to\b/i,
  /\bshall i\b/i,
];

function detectLazyStop(content) {
  if (!content || content.length < 30) return false;

  let matches = 0;
  for (const pattern of LAZY_STOP_PATTERNS) {
    if (pattern.test(content)) matches++;
  }

  if (matches === 0) return false;
  if (matches >= 2) return true;

  const trimmed = content.trim();
  if (trimmed.endsWith("?")) return true;

  if (/\n\s*\d+[.)]\s/m.test(content)) return true;

  return false;
}

module.exports = function(input) {
  const content = input.content || "";
  if (!detectLazyStop(content)) return null;

  return {
    decision: "block",
    reason: "auto-continue: lazy stop detected — blocking and injecting continuation prompt",
    reply: getStopMessage(),
  };
};
