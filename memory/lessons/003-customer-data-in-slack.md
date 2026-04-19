# Lesson: Customer Data Leaks to Slack Channels

## Observation
2026-04-19: Coconut posted customer-specific data (names, contacts, case numbers, account counts, infra details) to Slack #all-misfits twice in two days:
1. A Trello board update with customer names and account details
2. A Company 3 meeting prep with contact names, infra details, and security concerns

Both violated DATA-POLICY.md which restricts customer data from Slack channels. Joel caught both and had to delete them. The inner voice guardrail (Haiku review in coconut-guardrails) either didn't fire or didn't catch the pattern because the content was embedded in legitimate task output.

## The Lesson
Instructions and LLM review are insufficient for data classification enforcement. The model "knows" the policy but still violates it when focused on completing a task (task completion bias overrides policy awareness). Only deterministic hooks reliably block at send time.

When composing ANY outbound message for Slack, strip customer-identifiable data before writing. If the task requires customer data, post it to Teams instead.

## Source
- Session: 2026-04-19 Slack #all-misfits
- Conversation with: Joel, 2026-04-19 ~14:15 CDT
- Date observed: 2026-04-19

## Hook
- Has hook: yes
- Hook name: customer-data-gate
- Hook type: pre-action (before_tool_call on message send)
- Hook status: new
- Hook location: hook-runner-gates plugin (~/.openclaw/extensions/hook-runner-gates/index.ts)
- What it does: Scans outbound Slack messages for customer names, contacts, case numbers, email addresses, phone numbers, AWS account IDs, tenant UUIDs, MDR/workbench IDs, and internal infra patterns. Blocks with a redirect message telling the model to use Teams or sanitize.

## Retrieval Triggers
- Posting customer information to Slack
- Composing task updates that mention accounts/customers
- Trello card summaries with customer data
- Meeting prep with customer contacts
- "customer data in slack"
- "PII leak"
- DATA-POLICY.md enforcement
- Channel data classification

## Verification
- [ ] Hook fires when attempting to send customer name to #all-misfits
- [ ] Hook fires when attempting to send case number to #coco-chat
- [ ] Hook passes when sending to Teams (not Slack)
- [ ] Hook passes when sending generic internal content to Slack
- [ ] Hook fires on customer contact names (Dan Toresi, etc.)
- [ ] Hook fires on external email addresses
