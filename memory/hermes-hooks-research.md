# Hermes Agent — Pre-Tool-Use Hook Research

## Finding: Hermes HAS pre_tool_call blocking hooks ✅

### Hook Interface
```python
# Plugin returns:
{"action": "block", "message": "Reason the tool was blocked"}
```

### Available Hooks (VALID_HOOKS)
- `pre_tool_call` — fires BEFORE tool execution, can BLOCK with exit message
- `post_tool_call` — fires after tool execution
- `pre_llm_call` — fires before LLM API call
- `post_llm_call` — fires after LLM response
- `pre_api_request` — fires before API requests
- `post_api_request` — fires after API responses

### Plugin Registration
- User plugins: `~/.hermes/plugins/<name>/`
- Project plugins: `./.hermes/plugins/<name>/` (opt-in via env var)
- Pip plugins: entry-point group `hermes_agent.plugins`
- Each plugin needs: `plugin.yaml` manifest + `__init__.py` with `register(ctx)` function

### pre_tool_call Signature
```python
def pre_tool_call(tool_name: str, args: dict, task_id: str, session_id: str, tool_call_id: str) -> dict | None:
    # Return None to allow
    # Return {"action": "block", "message": "..."} to block
```

### Porting Map from Claude Code
| Claude Code Hook | Hermes Equivalent |
|-----------------|-------------------|
| PreToolUse (blocking) | `pre_tool_call` with `{"action": "block"}` |
| PostToolUse | `post_tool_call` |
| UserPromptSubmit | `pre_llm_call` (closest equivalent) |

### What Joel's Windows Claude Code enforces:
1. Active git worktree when updating wikis → check `args` for file paths, verify inside worktree
2. Commits every 15 file modifications → counter in plugin state, block writes after 15 without commit
3. Spec before work → check if spec file exists before allowing code changes
4. Todo.md updates from spec → verify todo.md modified when spec changes

### Next Steps
- [ ] Create a Hermes plugin at `~/.hermes/plugins/worktree-guard/`
- [ ] Port Joel's enforcement rules to `pre_tool_call` hooks
- [ ] Test blocking behavior with a simple "always block file_write" plugin
