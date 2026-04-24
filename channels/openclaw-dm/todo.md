# OpenClaw DM — Todo

## Pending

- [ ] **Design Haiku preprocessor gate** — Detect when Coconut takes any action without first writing a todo item to the appropriate channel's `todo.md` file. Should use a cheap Haiku call as a `before_tool_call` preprocessor to check: "Did the agent log this task before acting on it?" If not, block the action and redirect to write the todo first. This enforces task-tracking discipline at the hook level so it can't be skipped or forgotten.
  - *Source:* Joel, Slack DM, 2026-04-24 12:44 CDT
  - *Also:* After Joel corrections, block all action until metacognition check + lesson documented to memory

## Done

