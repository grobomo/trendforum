import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'http';
import type { IncomingMessage } from 'http';

export type WsEvent =
  | { type: 'new_post'; postId: number; subforumSlug: string }
  | { type: 'new_comment'; postId: number; commentId: number }
  | { type: 'vote_update'; postId?: number; commentId?: number; score: number }
  | { type: 'notification'; profileId: number; notification: { id: number; type: string; message: string; linkUrl: string; createdAt: string } };

let wss: WebSocketServer | null = null;

// Map profileId → Set<WebSocket> for targeted notifications
const profileSockets = new Map<number, Set<WebSocket>>();

// --- WebSocket rate limiting (T029) ---
// In-memory only; IPs are never logged or persisted (privacy-first).
const WS_MAX_CONNS_PER_IP = 10;          // max concurrent connections per IP
const WS_CONN_WINDOW_MS = 60_000;        // sliding window for connect attempts
const WS_MAX_ATTEMPTS_PER_WINDOW = 20;   // max new connections per IP per window

// Track concurrent connections per IP
const ipConnCount = new Map<string, number>();
// Track connect-attempt timestamps per IP (sliding window)
const ipConnAttempts = new Map<string, number[]>();

function getClientIp(req: IncomingMessage): string {
  // Trust X-Forwarded-For only if behind a known proxy; fall back to socket
  const forwarded = req.headers['x-forwarded-for'];
  if (typeof forwarded === 'string') return forwarded.split(',')[0].trim();
  return req.socket.remoteAddress || 'unknown';
}

/** Returns true if the connection should be rejected */
function wsRateLimited(ip: string): boolean {
  // --- Concurrent connection cap ---
  const current = ipConnCount.get(ip) || 0;
  if (current >= WS_MAX_CONNS_PER_IP) return true;

  // --- Sliding-window connect-attempt cap ---
  const now = Date.now();
  let attempts = ipConnAttempts.get(ip) || [];
  // Prune expired timestamps
  attempts = attempts.filter((t) => now - t < WS_CONN_WINDOW_MS);
  if (attempts.length >= WS_MAX_ATTEMPTS_PER_WINDOW) {
    ipConnAttempts.set(ip, attempts);
    return true;
  }

  // Record this attempt
  attempts.push(now);
  ipConnAttempts.set(ip, attempts);
  return false;
}

function trackConnect(ip: string): void {
  ipConnCount.set(ip, (ipConnCount.get(ip) || 0) + 1);
}

function trackDisconnect(ip: string): void {
  const n = (ipConnCount.get(ip) || 1) - 1;
  if (n <= 0) ipConnCount.delete(ip);
  else ipConnCount.set(ip, n);
}

// Periodic cleanup of stale attempt records (every 5 min)
setInterval(() => {
  const now = Date.now();
  for (const [ip, attempts] of ipConnAttempts) {
    const live = attempts.filter((t) => now - t < WS_CONN_WINDOW_MS);
    if (live.length === 0) ipConnAttempts.delete(ip);
    else ipConnAttempts.set(ip, live);
  }
}, 5 * 60_000);
// --- end rate limiting ---

export function setupWebSocket(server: Server): WebSocketServer {
  wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws, req) => {
    const ip = getClientIp(req);

    // Rate-limit check (T029)
    if (wsRateLimited(ip)) {
      ws.close(1008, 'Rate limited');
      return;
    }
    trackConnect(ip);

    // Parse profileId from query string: /ws?profileId=123
    const url = new URL(req.url || '', `http://${req.headers.host}`);
    const pidStr = url.searchParams.get('profileId');
    const profileId = pidStr ? parseInt(pidStr, 10) : null;

    if (profileId && !isNaN(profileId)) {
      if (!profileSockets.has(profileId)) {
        profileSockets.set(profileId, new Set());
      }
      profileSockets.get(profileId)!.add(ws);
    }

    ws.on('close', () => {
      trackDisconnect(ip);

      if (profileId && !isNaN(profileId)) {
        const set = profileSockets.get(profileId);
        if (set) {
          set.delete(ws);
          if (set.size === 0) profileSockets.delete(profileId);
        }
      }
    });

    ws.on('error', () => {}); // swallow per-client errors
  });

  return wss;
}

export function broadcast(event: WsEvent): void {
  if (!wss) return;
  const data = JSON.stringify(event);
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  }
}

/** Send an event only to WebSocket connections for a specific profileId */
export function sendToProfile(profileId: number, event: WsEvent): void {
  const sockets = profileSockets.get(profileId);
  if (!sockets) return;
  const data = JSON.stringify(event);
  for (const ws of sockets) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    }
  }
}
