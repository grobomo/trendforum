# Lesson: Managed Hooks vs Plugin SDK Hooks — Know the Boundaries

## Observation
2026-04-19: While building the self-improvement hook system, I initially assumed managed hooks (~/.openclaw/hooks/) could intercept tool calls. Joel caught this — managed hooks only receive event-level lifecycle hooks (message:sent, command:new, etc.). Tool-level interception (before_tool_call, after_tool_call) requires a proper Plugin SDK plugin registered via api.registerHook().

## The Lesson
Two separate hook systems exist in OpenClaw:
1. **Managed hooks** (~/.openclaw/hooks/) — event-level only: command:*, message:*, gateway:startup, agent:bootstrap, session:compact:*. Good for message audit, session lifecycle, context injection.
2. **Plugin SDK hooks** (via api.registerHook in a plugin) — full 28-hook set including before_tool_call (can block), after_tool_call (can audit), before_prompt_build, llm_input, llm_output, etc.

For behavioral blocking (stopping an action before it happens), you MUST use Plugin SDK hooks. Managed hooks can only audit after the fact.

## Source
- Docs: https://docs.openclaw.ai/automation/hooks (Event types table)
- Docs: https://docs.openclaw.ai/plugins/building-plugins (hook guard semantics)
- Type defs: dist/plugin-sdk/src/plugins/hook-types.d.ts (PluginHookName)
- Conversation with: Joel, 2026-04-19 11:33 CDT
- Date observed: 2026-04-19

## Hook
- Has hook: no (this is reference knowledge, not a behavioral pattern)
- Hook name: —
- Hook type: —
- Hook status: —

## Retrieval Triggers
- Building new hooks or hook modules
- Discussing hook architecture
- Wanting to intercept tool calls
- before_tool_call, after_tool_call
- Plugin vs managed hook decision
- "Can hooks block tool calls?"

## Verification
- N/A (knowledge lesson, not behavioral hook)
