import { readFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const RULES_PATH = join(homedir(), ".openclaw", "channel-rules.json");
const HAIKU_MODEL = "trendmicro-aiendpoint/claude-4.5-haiku";

// Cache rules in memory — only load once per gateway lifecycle
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

function findChannelRules(channelId: string, provider?: string): any {
  const rules = getRules();

  // Slack channels
  if (rules.slack?.[channelId]) return rules.slack[channelId];

  // Teams — match by provider hint
  if (provider === "teams") {
    // Could be group or private — default to group rules
    return rules.teams?.group || null;
  }

  // GitHub
  if (provider === "github") return rules.github || null;

  // Email
  if (provider === "email") return rules.email || null;

  return null;
}

async function askHaiku(message: string, channelRules: any): Promise<{ approved: boolean; reason?: string; suggestedChannel?: string }> {
  // Build the review prompt
  const prompt = `You are a message routing reviewer. Your ONLY job is to check if this outbound message belongs in the target channel.

TARGET CHANNEL: ${channelRules.name || "unknown"} 
PURPOSE: ${channelRules.purpose || "unknown"}
ALLOWED TOPICS: ${(channelRules.allows || []).join(", ")}
BLOCKED TOPICS: ${(channelRules.blocks || []).join(", ")}

MESSAGE TO REVIEW:
${message.substring(0, 500)}

Does this message align with the channel's purpose? Reply with EXACTLY one line:
APPROVE
or
BLOCK: <brief reason> → suggest: <better channel name>

Do not explain. Just APPROVE or BLOCK.`;

  try {
    // Use OpenClaw's gateway API to call Haiku
    const resp = await fetch("http://127.0.0.1:18789/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: HAIKU_MODEL,
        messages: [{ role: "user", content: prompt }],
        max_tokens: 60,
        temperature: 0,
      }),
    });

    if (!resp.ok) {
      console.warn(`[channel-topic-guard] Haiku call failed: ${resp.status}`);
      return { approved: true }; // fail-open
    }

    const data: any = await resp.json();
    const reply = (data.choices?.[0]?.message?.content || "").trim();

    if (reply.startsWith("BLOCK")) {
      const parts = reply.replace("BLOCK:", "").trim();
      const suggestMatch = parts.match(/→\s*suggest:\s*(.+)/i);
      return {
        approved: false,
        reason: parts.split("→")[0].trim(),
        suggestedChannel: suggestMatch?.[1]?.trim(),
      };
    }

    return { approved: true };
  } catch (err) {
    console.warn(`[channel-topic-guard] Haiku error: ${err}`);
    return { approved: true }; // fail-open on errors
  }
}

const handler = async (event: any) => {
  if (event.type !== "message" || event.action !== "sent") return;

  const channelId = event.context?.channelId || event.context?.to;
  const content = event.context?.content || "";
  const provider = event.context?.metadata?.provider || event.context?.provider || "";

  if (!channelId || !content || content.length < 20) return; // skip tiny messages

  const rules = findChannelRules(channelId, provider);
  if (!rules || (rules.blocks && rules.blocks.length === 0)) return; // no rules or no blocks = skip

  const result = await askHaiku(content, rules);

  if (!result.approved) {
    console.warn(
      `[channel-topic-guard] 🧠 BLOCKED in ${rules.name || channelId}: ${result.reason}` +
      (result.suggestedChannel ? ` → Redirect to: ${result.suggestedChannel}` : "")
    );
    // Push warning back to agent
    event.messages?.push(
      `⚠️ Inner voice: Your last message to ${rules.name || channelId} was flagged as off-topic. ` +
      `Reason: ${result.reason}` +
      (result.suggestedChannel ? ` Consider posting to ${result.suggestedChannel} instead.` : "")
    );
  }
};

export default handler;
