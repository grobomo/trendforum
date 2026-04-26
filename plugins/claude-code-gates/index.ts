/**
 * claude-code-gates — Modular directory-based plugin.
 *
 * Modules live under modules/<hook_type>/*.js (CommonJS). Each module exports
 * a single function that takes a Claude-Code style input and returns null
 * (pass) or a decision object. See modules/README or individual module files
 * for contract details.
 *
 *   modules/before_tool_call/   ← 17 gate .js files
 *   modules/after_tool_call/    ← 8 gate .js files
 *   modules/before_agent_reply/ ← 1 gate .js file
 *   modules/session_start/      ← 1 gate .js file
 *
 * Configuration:
 *   - modules.yaml (preferred) — per-hook enable/disable
 *   - pluginConfig.modules (flat fallback) — shared enable/disable
 *
 * Project-scoped subdirectories: modules/<hook>/<projectname>/*.js are only
 * loaded when basename(CLAUDE_PROJECT_DIR || cwd) === <projectname>.
 */

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import {
  appendFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  statSync,
  unlinkSync,
} from "node:fs";
import { basename, join } from "node:path";
import { homedir } from "node:os";

// ── Central Hook Log ───────────────────────────────────────────────────────

const HOOK_LOG_DIR = join(homedir(), ".openclaw", "logs");
const HOOK_LOG_PATH = join(HOOK_LOG_DIR, "audit-logger.jsonl");
const HOOK_LOG_MAX_BYTES = 10 * 1024 * 1024;

function ensureLogDir(): void {
  if (!existsSync(HOOK_LOG_DIR)) {
    mkdirSync(HOOK_LOG_DIR, { recursive: true });
  }
}

function rotateLogIfNeeded(): void {
  try {
    if (!existsSync(HOOK_LOG_PATH)) return;
    const stats = statSync(HOOK_LOG_PATH);
    if (stats.size >= HOOK_LOG_MAX_BYTES) {
      const rotatedPath = HOOK_LOG_PATH + ".1";
      if (existsSync(rotatedPath)) unlinkSync(rotatedPath);
      renameSync(HOOK_LOG_PATH, rotatedPath);
    }
  } catch {
    // non-fatal
  }
}

interface HookLogEntry {
  ts: string;
  event: string;
  module: string;
  result: "pass" | "block" | "text" | "skip";
  tool?: string;
  file?: string;
  cmd?: string;
  reason?: string;
  ms: number;
}

function logHookEvent(entry: HookLogEntry): void {
  try {
    ensureLogDir();
    rotateLogIfNeeded();
    appendFileSync(HOOK_LOG_PATH, JSON.stringify(entry) + "\n");
  } catch {
    // must never break the pipeline
  }
}

// ── Minimal YAML parser for modules.yaml ──────────────────────────────────
// Format: two-level nested map of booleans. Enough for this file, not general.

function parseModulesYaml(text: string): Record<string, Record<string, boolean>> {
  const result: Record<string, Record<string, boolean>> = {};
  const lines = text.split("\n");
  let topKey: string | null = null;
  let hookKey: string | null = null;

  for (const rawLine of lines) {
    const line = rawLine.replace(/\r$/, "");
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const indent = line.search(/\S/);
    const trimmed = line.trim();

    if (indent === 0 && trimmed.endsWith(":")) {
      topKey = trimmed.slice(0, -1).trim();
      hookKey = null;
      continue;
    }
    if (topKey !== "modules") continue;

    if (indent === 2 && trimmed.endsWith(":")) {
      hookKey = trimmed.slice(0, -1).trim();
      if (!result[hookKey]) result[hookKey] = {};
      continue;
    }
    if (indent >= 4 && hookKey) {
      const match = trimmed.match(/^([A-Za-z0-9_-]+)\s*:\s*(true|false)\s*$/);
      if (match) {
        result[hookKey][match[1]] = match[2] === "true";
      }
    }
  }
  return result;
}

// ── Module discovery ──────────────────────────────────────────────────────

type ModuleInput = Record<string, unknown>;
type ModuleFn = (input: ModuleInput) => unknown;

interface ModuleInfo {
  name: string;
  path: string;
  fn: ModuleFn;
  tools: string[] | null;
  requires: string[];
}

function parseModuleMetadata(filePath: string): { tools: string[] | null; requires: string[] } {
  let tools: string[] | null = null;
  let requires: string[] = [];
  try {
    const content = readFileSync(filePath, "utf-8");
    const lines = content.split("\n").slice(0, 8);
    for (const line of lines) {
      const toolsMatch = line.match(/^\s*\/\/\s*TOOLS:\s*(.+)$/i);
      if (toolsMatch) {
        tools = toolsMatch[1].split(",").map((t) => t.trim()).filter(Boolean);
      }
      const reqMatch = line.match(/^\s*\/\/\s*requires:\s*(.+)$/i);
      if (reqMatch) {
        requires = reqMatch[1].split(",").map((r) => r.trim()).filter(Boolean);
      }
    }
  } catch {
    // ignore — file unreadable
  }
  return { tools, requires };
}

function topologicalSort(modules: ModuleInfo[]): ModuleInfo[] {
  const byName = new Map(modules.map((m) => [m.name, m]));
  const visited = new Set<string>();
  const result: ModuleInfo[] = [];

  function visit(m: ModuleInfo, stack: Set<string>): void {
    if (visited.has(m.name)) return;
    if (stack.has(m.name)) return; // cycle — break
    stack.add(m.name);
    for (const dep of m.requires) {
      const depMod = byName.get(dep);
      if (depMod) visit(depMod, stack);
    }
    stack.delete(m.name);
    visited.add(m.name);
    result.push(m);
  }

  for (const m of modules) visit(m, new Set());
  return result;
}

function isDirectory(p: string): boolean {
  try { return lstatSync(p).isDirectory(); } catch { return false; }
}

function tryLoadModule(fullPath: string, name: string): ModuleInfo | null {
  try {
    delete require.cache[require.resolve(fullPath)];
    const fn = require(fullPath) as ModuleFn;
    if (typeof fn !== "function") {
      console.error(`[claude-code-gates] ${fullPath} did not export a function`);
      return null;
    }
    const meta = parseModuleMetadata(fullPath);
    return { name, path: fullPath, fn, tools: meta.tools, requires: meta.requires };
  } catch (e) {
    console.error(`[claude-code-gates] Failed to load ${fullPath}:`, (e as Error).message);
    return null;
  }
}

function loadModulesFromDir(dirPath: string, projectBasename: string): ModuleInfo[] {
  const modules: ModuleInfo[] = [];
  if (!existsSync(dirPath)) return modules;
  let entries: string[];
  try { entries = readdirSync(dirPath); } catch { return modules; }

  for (const entry of entries) {
    const fullPath = join(dirPath, entry);
    if (isDirectory(fullPath)) {
      if (entry !== projectBasename) continue;
      let subEntries: string[];
      try { subEntries = readdirSync(fullPath); } catch { continue; }
      for (const sub of subEntries) {
        if (!sub.endsWith(".js")) continue;
        const mod = tryLoadModule(join(fullPath, sub), basename(sub, ".js"));
        if (mod) modules.push(mod);
      }
      continue;
    }
    if (!entry.endsWith(".js")) continue;
    const mod = tryLoadModule(fullPath, basename(entry, ".js"));
    if (mod) modules.push(mod);
  }

  return topologicalSort(modules);
}

// ── Event adaptation (OpenClaw → Claude Code module contract) ────────────

function adaptToolInput(params: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...params };
  if (!out.file_path && (params as { path?: unknown }).path !== undefined) {
    out.file_path = (params as { path?: unknown }).path;
  }
  return out;
}

function extractLogContext(toolName: string, params: Record<string, unknown>): { file?: string; cmd?: string } {
  const out: { file?: string; cmd?: string } = {};
  if (toolName === "Bash" || toolName === "exec") {
    const cmd = String((params as { command?: unknown }).command || "").trim();
    if (cmd) out.cmd = cmd.slice(0, 120);
  } else {
    const p = (params as { path?: unknown; file_path?: unknown });
    const fp = String(p.path || p.file_path || "");
    if (fp) out.file = basename(fp);
  }
  return out;
}

// ═══════════════════════════════════════════════════════════════════════════
// PLUGIN ENTRY POINT
// ═══════════════════════════════════════════════════════════════════════════

export default definePluginEntry({
  id: "claude-code-gates",
  name: "Hook Runner Gates",
  description:
    "Modular hook-runner gates for OpenClaw. Directory-organized modules for " +
    "before_tool_call, after_tool_call, before_agent_reply, and session_start hooks.",

  register(api) {
    const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();
    const projectBasename = basename(projectDir);

    // Load modules.yaml if present (preferred config source)
    let yamlConfig: Record<string, Record<string, boolean>> = {};
    const yamlPath = join(__dirname, "modules.yaml");
    if (existsSync(yamlPath)) {
      try {
        yamlConfig = parseModulesYaml(readFileSync(yamlPath, "utf-8"));
      } catch {
        // ignore — fall back to pluginConfig
      }
    }

    function isModuleEnabled(hookType: string, moduleName: string): boolean {
      if (yamlConfig[hookType] && yamlConfig[hookType][moduleName] !== undefined) {
        return yamlConfig[hookType][moduleName];
      }
      const cfg = (api.pluginConfig as { modules?: Record<string, boolean> }) || {};
      if (cfg.modules && cfg.modules[moduleName] !== undefined) {
        return cfg.modules[moduleName];
      }
      return true;
    }

    const beforeModules = loadModulesFromDir(join(__dirname, "modules", "before_tool_call"), projectBasename);
    const afterModules = loadModulesFromDir(join(__dirname, "modules", "after_tool_call"), projectBasename);
    const replyModules = loadModulesFromDir(join(__dirname, "modules", "before_agent_reply"), projectBasename);
    const sessionModules = loadModulesFromDir(join(__dirname, "modules", "session_start"), projectBasename);

    // ── before_tool_call ─────────────────────────────────────────────────
    api.on("before_tool_call", async (event, _ctx) => {
      const toolName = event.toolName;
      const rawParams = (event.params || {}) as Record<string, unknown>;
      const toolInput = adaptToolInput(rawParams);
      const logCtx = extractLogContext(toolName, rawParams);

      for (const mod of beforeModules) {
        if (!isModuleEnabled("before_tool_call", mod.name)) {
          logHookEvent({ ts: new Date().toISOString(), event: "PreToolUse", module: mod.name, result: "skip", tool: toolName, ...logCtx, ms: 0 });
          continue;
        }
        if (mod.tools && !mod.tools.includes(toolName)) continue;

        const t0 = Date.now();
        let out: unknown = null;
        try {
          out = mod.fn({ tool_name: toolName, tool_input: toolInput });
        } catch (e) {
          console.error(`[claude-code-gates] Module ${mod.name} crashed:`, (e as Error).message);
        }
        const ms = Date.now() - t0;

        const r = out as { decision?: string; reason?: string } | null;
        if (r && r.decision === "block") {
          logHookEvent({
            ts: new Date().toISOString(), event: "PreToolUse", module: mod.name,
            result: "block", tool: toolName, ...logCtx,
            reason: (r.reason || "").slice(0, 200), ms,
          });
          return { block: true, blockReason: r.reason };
        }
        logHookEvent({ ts: new Date().toISOString(), event: "PreToolUse", module: mod.name, result: "pass", tool: toolName, ...logCtx, ms });
      }

      return undefined;
    });

    // ── after_tool_call ──────────────────────────────────────────────────
    api.on("after_tool_call", async (event, _ctx) => {
      const toolName = event.toolName;
      const rawParams = (event.params || {}) as Record<string, unknown>;
      const toolInput = adaptToolInput(rawParams);
      const resultStr = (event as Record<string, unknown>).result as string | undefined;
      const logCtx = extractLogContext(toolName, rawParams);

      for (const mod of afterModules) {
        if (!isModuleEnabled("after_tool_call", mod.name)) {
          logHookEvent({ ts: new Date().toISOString(), event: "PostToolUse", module: mod.name, result: "skip", tool: toolName, ...logCtx, ms: 0 });
          continue;
        }
        if (mod.tools && !mod.tools.includes(toolName)) continue;

        const t0 = Date.now();
        let out: unknown = null;
        try {
          out = mod.fn({ tool_name: toolName, tool_input: toolInput, result: resultStr });
        } catch (e) {
          console.error(`[claude-code-gates] Module ${mod.name} crashed:`, (e as Error).message);
        }
        const ms = Date.now() - t0;

        const r = out as { message?: string } | null;
        if (r && r.message) {
          logHookEvent({
            ts: new Date().toISOString(), event: "PostToolUse", module: mod.name,
            result: "text", tool: toolName, ...logCtx,
            reason: r.message.slice(0, 200), ms,
          });
          return { message: r.message };
        }
        logHookEvent({ ts: new Date().toISOString(), event: "PostToolUse", module: mod.name, result: "pass", tool: toolName, ...logCtx, ms });
      }

      return undefined;
    });

    // ── before_agent_reply ───────────────────────────────────────────────
    api.on("before_agent_reply", async (event, _ctx) => {
      const e = event as { cleanedBody?: string; content?: string };
      const content = e.cleanedBody || e.content || "";

      for (const mod of replyModules) {
        if (!isModuleEnabled("before_agent_reply", mod.name)) {
          logHookEvent({ ts: new Date().toISOString(), event: "Stop", module: mod.name, result: "skip", ms: 0 });
          continue;
        }

        const t0 = Date.now();
        let out: unknown = null;
        try {
          out = mod.fn({ content });
        } catch (err) {
          console.error(`[claude-code-gates] Module ${mod.name} crashed:`, (err as Error).message);
        }
        const ms = Date.now() - t0;

        const r = out as { decision?: string; reason?: string; reply?: string } | null;
        if (r && r.decision === "block") {
          logHookEvent({
            ts: new Date().toISOString(), event: "Stop", module: mod.name, result: "block",
            reason: (r.reason || "").slice(0, 200), ms,
          });
          return {
            handled: true,
            reply: { text: r.reply || "" },
            reason: r.reason,
          };
        }
        logHookEvent({ ts: new Date().toISOString(), event: "Stop", module: mod.name, result: "pass", ms });
      }

      return undefined;
    });

    // ── session_start (via before_agent_start for prompt injection) ──────
    api.on("before_agent_start", async (_event, _ctx) => {
      const suffixes: string[] = [];
      for (const mod of sessionModules) {
        if (!isModuleEnabled("session_start", mod.name)) {
          logHookEvent({ ts: new Date().toISOString(), event: "AgentStart", module: mod.name, result: "skip", ms: 0 });
          continue;
        }

        const t0 = Date.now();
        let out: unknown = null;
        try {
          out = mod.fn({});
        } catch (e) {
          console.error(`[claude-code-gates] Module ${mod.name} crashed:`, (e as Error).message);
        }
        const ms = Date.now() - t0;

        const r = out as { text?: string } | null;
        if (r && r.text) {
          suffixes.push(r.text);
          logHookEvent({ ts: new Date().toISOString(), event: "AgentStart", module: mod.name, result: "text", reason: r.text.slice(0, 200), ms });
        } else {
          logHookEvent({ ts: new Date().toISOString(), event: "AgentStart", module: mod.name, result: "pass", ms });
        }
      }

      if (suffixes.length > 0) {
        return { systemPromptSuffix: suffixes.join("\n\n") };
      }
      return undefined;
    });
  },
});
