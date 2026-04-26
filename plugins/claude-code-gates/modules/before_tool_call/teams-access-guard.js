// TOOLS: Bash,exec
// WHY: Enforce CHAT-ACCESS-POLICY.md — block writes to non-read-write Teams chats at API layer.
// REQUIRES: none
//
// This is the "hardware guard" — a bug in compose logic can't bypass it because
// this gate runs before the tool call reaches the shell.
//
// Enforcement points:
//   1. Pre-send: reject queue_reply.py / send_direct.py / send_reply.py to read-only/disabled chats
//   2. Content scan: block outbound messages containing API keys, tokens, PII
//   3. Cross-chat isolation: reject commands that pipe from one chat context to another
//   4. Raw Graph API: block direct curl POST to /me/chats/{id}/messages for non-rw chats

const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { homedir } = require("node:os");
const { SECRET_PATTERNS } = require("../../_helpers.js");

// ── Config loader ──────────────────────────────────────────────────────────

const CONFIG_PATH = join(
  homedir(),
  ".openclaw",
  "workspace",
  "scripts",
  "teams-poller",
  "config.json"
);

let _configCache = null;
let _configMtime = 0;

function loadConfig() {
  try {
    const { mtimeMs } = require("node:fs").statSync(CONFIG_PATH);
    if (_configCache && mtimeMs === _configMtime) return _configCache;
    _configCache = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
    _configMtime = mtimeMs;
    return _configCache;
  } catch {
    return { chats: [] };
  }
}

function getChatAccess(chatId) {
  const config = loadConfig();
  for (const c of config.chats || []) {
    if (c.id === chatId) return c.access || "read-write";
  }
  // Unknown chat — default policy: DMs disabled, groups read-only
  if (chatId.includes("@unq.gbl.spaces")) return "disabled";
  return "read-only";
}

function getChatLabel(chatId) {
  const config = loadConfig();
  for (const c of config.chats || []) {
    if (c.id === chatId) return c.label || chatId.slice(0, 30);
  }
  return chatId.slice(0, 30);
}

function resolveLabelToId(label) {
  const config = loadConfig();
  const lower = label.toLowerCase();
  // Exact match
  for (const c of config.chats || []) {
    if ((c.label || "").toLowerCase() === lower) return c.id;
  }
  // Partial match
  for (const c of config.chats || []) {
    if ((c.label || "").toLowerCase().includes(lower)) return c.id;
  }
  return null;
}

// ── Chat ID extraction ─────────────────────────────────────────────────────

// Teams chat ID pattern: 19:xxx@thread.v2 or 19:xxx@unq.gbl.spaces
const CHAT_ID_RE = /19:[a-f0-9-]+(?:@thread\.v2|@unq\.gbl\.spaces)/g;

function extractChatIds(cmd) {
  const ids = new Set();
  const matches = cmd.match(CHAT_ID_RE);
  if (matches) matches.forEach((m) => ids.add(m));
  return [...ids];
}

// ── Send command detection ─────────────────────────────────────────────────

const SEND_SCRIPTS_RE = /(?:queue_reply|send_reply|send_direct|send_card|send_reaction)\.py/;
const GRAPH_POST_RE = /\/me\/chats\/[^/]+\/messages/;

function isSendCommand(cmd) {
  return SEND_SCRIPTS_RE.test(cmd) || GRAPH_POST_RE.test(cmd);
}

// ── Chat target extraction from --chat-id / --chat args ────────────────────

function extractChatArg(cmd) {
  // --chat-id 19:abc@thread.v2
  const idMatch = cmd.match(/--chat-id\s+['"]?(19:[^\s'"]+)/);
  if (idMatch) return { type: "id", value: idMatch[1] };

  // --chat "Some Label"
  const labelMatch = cmd.match(/--chat\s+['"]([^'"]+)['"]/);
  if (labelMatch) return { type: "label", value: labelMatch[1] };
  const labelMatch2 = cmd.match(/--chat\s+(\S+)/);
  if (labelMatch2 && !labelMatch2[1].startsWith("19:"))
    return { type: "label", value: labelMatch2[1] };

  return null;
}

// ── PII patterns (beyond secrets — email, SSN, phone) ──────────────────────

const PII_PATTERNS = [
  { name: "Email Address", re: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, minLen: 10 },
  { name: "SSN", re: /\b\d{3}-\d{2}-\d{4}\b/g },
  { name: "Credit Card", re: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b/g },
];

// ── Content scanning ───────────────────────────────────────────────────────

function scanContent(cmd) {
  // Extract the message body from stdin redirect, heredoc, or echo pipe
  let body = "";

  // heredoc: <<'EOF' ... EOF or << EOF ... EOF
  const heredocMatch = cmd.match(/<<\s*['"]?(\w+)['"]?\s*\n?([\s\S]*?)\n\1/);
  if (heredocMatch) body = heredocMatch[2];

  // echo "..." | python3 queue_reply.py
  const echoMatch = cmd.match(/echo\s+["']([^"']+)["']\s*\|/);
  if (echoMatch) body += " " + echoMatch[1];

  // cat /tmp/... — we can't read the file, but flag if it's a suspicious path
  // (the Python scripts already check stdin, this is defense in depth)

  if (!body.trim()) return []; // Can't scan stdin-only; Python layer handles it

  const findings = [];

  // Check for secrets (reuse existing patterns from _helpers.js)
  for (const pat of SECRET_PATTERNS) {
    if (pat.re.test(body)) {
      findings.push(`Secret leak: ${pat.name}`);
    }
  }

  // Check for PII
  for (const pat of PII_PATTERNS) {
    const matches = body.match(pat.re);
    if (matches && matches.length > 0) {
      // Don't flag single email addresses in "from" context — they're normal
      if (pat.name === "Email Address" && matches.length <= 1) continue;
      findings.push(`PII: ${pat.name} (${matches.length} occurrence(s))`);
    }
  }

  return findings;
}

// ── Audit logging ──────────────────────────────────────────────────────────

const AUDIT_LOG_PATH = join(homedir(), ".openclaw", "logs", "teams-access-audit.jsonl");
const AUDIT_MAX_BYTES = 5 * 1024 * 1024;

function auditLog(entry) {
  try {
    const { appendFileSync, existsSync, statSync, renameSync, unlinkSync, mkdirSync } = require("node:fs");
    const dir = join(homedir(), ".openclaw", "logs");
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

    // Rotate if too large
    if (existsSync(AUDIT_LOG_PATH)) {
      const stats = statSync(AUDIT_LOG_PATH);
      if (stats.size >= AUDIT_MAX_BYTES) {
        const rotated = AUDIT_LOG_PATH + ".1";
        if (existsSync(rotated)) unlinkSync(rotated);
        renameSync(AUDIT_LOG_PATH, rotated);
      }
    }

    appendFileSync(AUDIT_LOG_PATH, JSON.stringify({
      ts: new Date().toISOString(),
      ...entry,
    }) + "\n");
  } catch {
    // Never break the pipeline
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN GATE
// ══════════════════════════════════════════════════════════════════════════════

module.exports = function (input) {
  const cmd = String((input.tool_input || {}).command || "");
  if (!cmd) return null;

  // Only care about Teams send operations
  if (!isSendCommand(cmd)) return null;

  // ── 1. Resolve target chat ──────────────────────────────────────────────

  let targetChatId = null;
  let targetLabel = null;

  // Try explicit --chat-id / --chat arg first
  const chatArg = extractChatArg(cmd);
  if (chatArg) {
    if (chatArg.type === "id") {
      targetChatId = chatArg.value;
    } else {
      targetChatId = resolveLabelToId(chatArg.value);
      targetLabel = chatArg.value;
    }
  }

  // Try extracting from raw chat IDs in the command
  if (!targetChatId) {
    const chatIds = extractChatIds(cmd);
    if (chatIds.length === 1) targetChatId = chatIds[0];
  }

  // ── 2. Access policy enforcement ────────────────────────────────────────

  if (targetChatId) {
    const access = getChatAccess(targetChatId);
    const label = targetLabel || getChatLabel(targetChatId);

    // Audit every send attempt
    auditLog({
      action: "send_attempt",
      chat_id: targetChatId,
      chat_label: label,
      access: access,
      script: cmd.match(SEND_SCRIPTS_RE)?.[0] || "direct",
      cmd_preview: cmd.slice(0, 120),
    });

    if (access === "disabled") {
      auditLog({ action: "BLOCKED", chat_id: targetChatId, chat_label: label, reason: "disabled" });
      return {
        decision: "block",
        reason:
          `🚫 TEAMS ACCESS GUARD: Chat "${label}" is DISABLED.\n` +
          `Policy: DMs are disabled by default (opt-in only).\n` +
          `This chat must be explicitly enabled in config.json before sending.\n` +
          `See: scripts/teams-poller/CHAT-ACCESS-POLICY.md`,
      };
    }

    if (access === "read-only") {
      auditLog({ action: "BLOCKED", chat_id: targetChatId, chat_label: label, reason: "read-only" });
      return {
        decision: "block",
        reason:
          `🚫 TEAMS ACCESS GUARD: Chat "${label}" is READ-ONLY.\n` +
          `Policy: Write access must be explicitly set to "read-write" in config.json.\n` +
          `For important items, flag them to Joel via Slack DM instead.\n` +
          `See: scripts/teams-poller/CHAT-ACCESS-POLICY.md`,
      };
    }
  }

  // ── 3. Cross-chat isolation check ───────────────────────────────────────

  const allChatIds = extractChatIds(cmd);
  if (allChatIds.length > 1) {
    auditLog({
      action: "BLOCKED",
      reason: "cross-chat",
      chats: allChatIds.map((id) => getChatLabel(id)),
    });
    return {
      decision: "block",
      reason:
        `🚫 TEAMS ACCESS GUARD: Cross-chat operation detected.\n` +
        `Command references ${allChatIds.length} different chat IDs.\n` +
        `Each send must target exactly one chat to prevent context bleed.\n` +
        `Chats: ${allChatIds.map((id) => getChatLabel(id)).join(", ")}`,
    };
  }

  // ── 4. Content scanning (DLP) ──────────────────────────────────────────

  const contentFindings = scanContent(cmd);
  if (contentFindings.length > 0) {
    const label = targetChatId ? getChatLabel(targetChatId) : "unknown";
    auditLog({
      action: "BLOCKED",
      chat_label: label,
      reason: "content_scan",
      findings: contentFindings,
    });
    return {
      decision: "block",
      reason:
        `🚫 TEAMS ACCESS GUARD: Content scan flagged potential sensitive data:\n` +
        contentFindings.map((f) => `  • ${f}`).join("\n") +
        `\n\nRemove sensitive data before sending. Use environment variables or ` +
        `credential references instead of raw values.`,
    };
  }

  // ── 5. Direct Graph API guard ───────────────────────────────────────────

  if (GRAPH_POST_RE.test(cmd) && /curl.*-X\s*POST/i.test(cmd)) {
    // Direct Graph API call — extra audit but allow if chat is read-write
    const graphChatMatch = cmd.match(/\/me\/chats\/([^/]+)\/messages/);
    if (graphChatMatch) {
      const graphChatId = graphChatMatch[1];
      // URL-encoded chat IDs need decoding
      const decoded = decodeURIComponent(graphChatId);
      const access = getChatAccess(decoded);
      if (access !== "read-write") {
        auditLog({
          action: "BLOCKED",
          reason: "direct_graph_api",
          chat_id: decoded,
          access: access,
        });
        return {
          decision: "block",
          reason:
            `🚫 TEAMS ACCESS GUARD: Direct Graph API POST blocked.\n` +
            `Chat "${getChatLabel(decoded)}" access is "${access}" — only read-write chats allow sends.\n` +
            `Use queue_reply.py with proper chat targeting instead of raw API calls.`,
        };
      }
    }
    auditLog({
      action: "direct_graph_api_allowed",
      cmd_preview: cmd.slice(0, 120),
    });
  }

  // All checks passed
  return null;
};
