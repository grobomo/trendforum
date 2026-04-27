import { useEffect, useRef, useCallback } from 'react';

export type WsEvent =
  | { type: 'new_post'; postId: number; subforumSlug: string }
  | { type: 'new_comment'; postId: number; commentId: number }
  | { type: 'vote_update'; postId?: number; commentId?: number; score: number }
  | { type: 'notification'; profileId: number; notification: { id: number; type: string; message: string; linkUrl: string; createdAt: string } };

export function useWebSocket(onEvent: (event: WsEvent) => void, profileId?: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const qs = profileId ? `?profileId=${profileId}` : '';
    const ws = new WebSocket(`${proto}//${location.host}/ws${qs}`);

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as WsEvent;
        cbRef.current(event);
      } catch {}
    };

    ws.onclose = () => {
      // Reconnect after 3s
      setTimeout(() => {
        if (wsRef.current === ws) connect();
      }, 3000);
    };

    ws.onerror = () => ws.close();

    wsRef.current = ws;
  }, [profileId]);

  useEffect(() => {
    connect();
    return () => {
      const ws = wsRef.current;
      wsRef.current = null;
      ws?.close();
    };
  }, [connect]);
}
