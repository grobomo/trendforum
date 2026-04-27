import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'http';

export type WsEvent =
  | { type: 'new_post'; postId: number; subforumSlug: string }
  | { type: 'new_comment'; postId: number; commentId: number }
  | { type: 'vote_update'; postId?: number; commentId?: number; score: number };

let wss: WebSocketServer | null = null;

export function setupWebSocket(server: Server): WebSocketServer {
  wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws) => {
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
