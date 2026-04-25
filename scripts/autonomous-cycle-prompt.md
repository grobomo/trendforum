Autonomous operation cycle. You have blanket permission to act. Execute in order:

1. SESSION HEALTH: Run `python3 /home/ubu/.openclaw/workspace/scripts/session-health/monitor.py`. It auto-resets sessions >15MB or >15 compactions, cleans orphaned files.
2. SLACK SCAN: Check all Slack channels for unresponded human messages. Respond to any that need it. Use state_manager.py check/done to throttle.
3. TRELLO WORK: Pull Coconut Todo list (6954d3af836b51597afff8e9). Pick the highest priority card and DO THE WORK — not just review it. Mark dueComplete=true when done.
4. CLAUDE TABS: Run manage.py monitor. Close completed tabs, investigate stuck ones.
5. SELF-AUDIT: Run `python3 /home/ubu/openclaw-dm/scripts/metacognition/self-audit.py`. Fix any failures.
6. METACOGNITION: Quick self-review (2-3 sentences max). Am I repeating mistakes? Violating lessons? Append to memory/metacognition/YYYY-MM-DD.md.
7. SCHEDULE: If /tmp/schedule-briefing-latest.json is fresh and unposted, synthesize and post to #scheduling (C0ATK8YJQD9).
8. CONTINUE: If time remains, keep working on the next Trello card. Never idle while cards exist.

Rules:
- Do NOT reply HEARTBEAT_OK if open tasks exist. Do the work.
- Do NOT ask "should I continue?" — the answer is always yes.
- Report what you DID, not what you COULD do.
- Only pause for: external customer emails, public posts, infra deletion, spending money.
- ALWAYS read ~/openclaw-dm/dm/todo.md FIRST before any work. Update it with what you're doing. The todo-enforcement hook will BLOCK you otherwise.
- Post metacognition updates to #coco-metacognition (C0ATCRVSB71) so Joel has visibility.
