import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getNotifications,
  markNotificationsRead,
  deleteNotification,
  NotificationItem,
} from '../lib/api';

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadNotifications = useCallback(async () => {
    try {
      const { notifications: items, unreadCount: count } = await getNotifications(false, 100);
      setNotifications(items);
      setUnreadCount(count);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkAllRead = async () => {
    try {
      await markNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {}
  };

  const handleClick = async (n: NotificationItem) => {
    if (!n.read) {
      try {
        await markNotificationsRead([n.id]);
        setNotifications((prev) =>
          prev.map((item) => (item.id === n.id ? { ...item, read: true } : item)),
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {}
    }
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

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-8 px-4">
        <div className="text-forum-muted text-center py-12">Loading notifications…</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Notifications</h1>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="text-sm text-forum-accent hover:underline"
          >
            Mark all as read
          </button>
        )}
      </div>

      {/* Notification list */}
      {notifications.length === 0 ? (
        <div className="bg-forum-card border border-forum-border rounded-lg px-6 py-16 text-center">
          <svg
            className="w-12 h-12 mx-auto text-forum-muted mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          <p className="text-forum-muted text-sm">No notifications yet</p>
          <p className="text-forum-muted/60 text-xs mt-1">
            You'll see replies, mentions, and votes here
          </p>
        </div>
      ) : (
        <div className="bg-forum-card border border-forum-border rounded-lg overflow-hidden divide-y divide-forum-border/50">
          {notifications.map((n) => (
            <button
              key={n.id}
              onClick={() => handleClick(n)}
              className={`w-full text-left px-4 py-3 hover:bg-forum-bg/50 transition group ${
                !n.read ? 'bg-forum-bg/30' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Blue dot for unread */}
                <div className="w-4 flex-shrink-0 pt-1.5">
                  {!n.read && (
                    <span className="block w-2 h-2 rounded-full bg-blue-500" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className={`text-sm ${
                      n.read ? 'text-forum-muted' : 'text-[#e0e0e0]'
                    }`}
                  >
                    {n.message}
                  </p>
                  <span className="text-xs text-forum-muted/70 mt-0.5 inline-block">
                    {timeAgo(n.createdAt)}
                  </span>
                </div>

                {/* Delete button */}
                <button
                  onClick={(e) => handleDelete(e, n.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-forum-muted hover:text-[#D5232F] transition flex-shrink-0"
                  aria-label="Delete notification"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
