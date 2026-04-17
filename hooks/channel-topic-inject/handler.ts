import { readFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const RULES_PATH = join(homedir(), ".openclaw", "channel-rules.json");

// Track which channels we've already injected rules for this session
const _injected = new Set<string>();

let _rules: any = null;
function getRules(): any {
  if (!_rules) {
    try {
      _rules = JSON.parse(readFileSync(RULES_PATH, "utf-8"));
    } catch {
      _rules = {};
    }
  }
  return _rules;
}

const handler = async (event: any) => {
  if (event.type !== "message" || event.action !== "received") return;

  const channelId = event.context?.channelId;
  if (!channelId) return;

  // Only inject once per channel per gateway lifecycle
  if (_injected.has(channelId)) return;

  const rules = getRules();
  const channelRules = rules.slack?.[channelId];
  if (!channelRules) return;

  _injected.add(channelId);

  event.messages.push(
    `[Channel rules loaded] ${channelRules.name}: ${channelRules.purpose}. ` +
    `Allowed: ${(channelRules.allows || []).join(", ")}. ` +
    `Blocked: ${(channelRules.blocks || []).join(", ")}.`
  );
};

export default handler;
