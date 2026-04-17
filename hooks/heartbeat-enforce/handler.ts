/**
 * Heartbeat Enforce Hook
 * 
 * Intercepts heartbeat messages and injects enforcement instructions
 * to ensure the agent reads and follows HEARTBEAT.md strictly.
 */

const HEARTBEAT_PATTERNS = [
  'heartbeat',
  'HEARTBEAT_OK',
  'Read HEARTBEAT.md',
  'heartbeat poll',
];

const ENFORCEMENT_MESSAGE = `
⚠️ HEARTBEAT ENFORCEMENT (injected by hook):
You MUST read workspace file HEARTBEAT.md and execute EVERY task listed.
Do NOT respond HEARTBEAT_OK without completing all tasks.
If HEARTBEAT.md has actionable items, do them NOW before responding.
If HEARTBEAT.md is empty or has only comments, respond HEARTBEAT_OK.
`.trim();

const handler = async (event: any) => {
  if (event.type !== 'message' || event.action !== 'received') {
    return;
  }

  const content = event.context?.content || '';
  
  // Check if this is a heartbeat message
  const isHeartbeat = HEARTBEAT_PATTERNS.some(pattern => 
    content.toLowerCase().includes(pattern.toLowerCase())
  );

  if (isHeartbeat) {
    // Inject enforcement reminder into the message flow
    event.messages.push(ENFORCEMENT_MESSAGE);
  }
};

export default handler;
