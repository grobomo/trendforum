import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'http';

export type WsEvent =
  | { type: 'new_post'; postId: number; subforumSlug: string }
  | { type: 'new_comment'; postId: number; commentId: number }
  | { type: 'vote_update'; postId?: number; commentId?: number; score: number }
  | { type: 'notification'; profileId: number; notification: { id: number; type: string; message: string; linkUrl: string; createdAt: string } };

let wss: WebSocketServer | null = null;

// Map profileId → Set<WebSocket> for targeted notifications
const profileSockets = new Map<number, Set<WebSocket>>();

export function setupWebSocket(server: Server): WebSocketServer {
  wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws, req) => {
    // Parse profileId from query string: /ws?profileId=123
    const url = new URL(req.url || '', `http://${req.headers.host}`);
    const pidStr = url.searchParams.get('profileId');
    const profileId = pidStr ? parseInt(pidStr, 10) : null;

    if (profileId && !isNaN(profileId)) {
      if (!profileSockets.has(profileId)) {
        profileSockets.set(profileId, new Set());
      }
      profileSockets.get(profileId)!.add(ws);

      ws.on('close', () => {
        const set = profileSockets.get(profileId);
        if (set) {
          set.delete(ws);
          if (set.size === 0) profileSockets.delete(profileId);
        }
      });
    }

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
