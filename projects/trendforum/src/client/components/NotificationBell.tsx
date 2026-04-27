import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getNotifications,
  markNotificationsRead,
  deleteNotification,
  NotificationItem,
} from '../lib/api';
import { useWebSocket, WsEvent } from '../hooks/useWebSocket';

interface Props {
  profileId: number;
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

/** Play a short "ding" notification sound using Web Audio API */
function playNotificationSound() {
  // Check user preference (default: enabled)
  const pref = localStorage.getItem('tf_notification_sound');
  if (pref === 'false') return;

  // Don't play if tab is hidden
  if (document.hidden) return;

  try {
    const ctx = new AudioContext();
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(520, ctx.currentTime);
    oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.08);

    gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);

    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.2);

    oscillator.onended = () => ctx.close();
  } catch {
    // AudioContext not available, silently ignore
  }
}

export function NotificationBell({ profileId }: Props) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Load notifications on mount
  useEffect(() => {
    getNotifications(false, 30)
      .then(({ notifications: items, unreadCount: count }) => {
        setNotifications(items);
        setUnreadCount(count);
      })
      .catch(() => {});
  }, [profileId]);

  // Real-time notifications via WebSocket
  useWebSocket(
    useCallback((event: WsEvent) => {
      if (event.type === 'notification' && event.profileId === profileId) {
        const n = event.notification as NotificationItem;
        setNotifications((prev) => [{ ...n, read: false }, ...prev].slice(0, 50));
        setUnreadCount((c) => c + 1);
        playNotificationSound();
      }
    }, [profileId]),
    profileId,
  );

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClick);
      return () => document.removeEventListener('mousedown', handleClick);
    }
  }, [open]);

  const handleToggle = () => {
    setOpen((o) => !o);
    // Refresh when opening
    if (!open) {
      getNotifications(false, 30)
        .then(({ notifications: items, unreadCount: count }) => {
          setNotifications(items);
          setUnreadCount(count);
        })
        .catch(() => {});
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {}
  };

  const handleClickNotification = async (n: NotificationItem) => {
    // Mark this one as read
    if (!n.read) {
      try {
        await markNotificationsRead([n.id]);
        setNotifications((prev) =>
          prev.map((item) => (item.id === n.id ? { ...item, read: true } : item)),
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {}
    }
    setOpen(false);
    navigate(n.linkUrl);
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await deleteNotification(id);
      const deleted = notifications.find((n) => n.id === id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (deleted && !deleted.read) {
        setUnreadCount((c) => Math.max(0, c - 1));
      }
    } catch {}
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={handleToggle}
        className="relative p-1 text-forum-muted hover:text-forum-accent transition"
        aria-label="Notifications"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-[#D5232F] text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 flex items-center justify-center px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-h-96 bg-forum-card border border-forum-border rounded-lg shadow-xl overflow-hidden z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-forum-border">
            <span className="text-sm font-semibold text-white">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-forum-accent hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto max-h-72">
            {notifications.length === 0 ? (
              <div className="px-3 py-8 text-center text-sm text-forum-muted">
                No notifications yet
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleClickNotification(n)}
                  className={`w-full text-left px-3 py-2.5 border-b border-forum-border/50 hover:bg-forum-bg/50 transition group ${
                    !n.read ? 'bg-forum-bg/30' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {!n.read && (
                      <span className="mt-1.5 w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                    )}
                    <div className={`flex-1 min-w-0 ${n.read ? 'ml-4' : ''}`}>
                      <p className={`text-sm line-clamp-2 ${n.read ? 'text-forum-muted' : 'text-[#e0e0e0]'}`}>{n.message}</p>
                      <span className="text-xs text-forum-muted">{timeAgo(n.createdAt)}</span>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, n.id)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 text-forum-muted hover:text-[#D5232F] transition flex-shrink-0"
                      aria-label="Delete notification"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* See all link */}
          <div className="border-t border-forum-border px-3 py-2 text-center">
            <button
              onClick={() => { setOpen(false); navigate('/notifications'); }}
              className="text-xs text-forum-accent hover:underline"
            >
              See all notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationBell;
