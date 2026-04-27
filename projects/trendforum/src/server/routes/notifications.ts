import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';

const router = Router();

/**
 * GET /api/notifications
 * Returns unread + recent notifications for the current profile.
 * Query: ?unreadOnly=true (default false), ?limit=50
 */
router.get('/', requireAuth, async (req, res) => {
  const profileId = req.tokenPayload!.profileId;
  if (!profileId) {
    res.json({ notifications: [], unreadCount: 0 });
    return;
  }

  const unreadOnly = req.query.unreadOnly === 'true';
  const limit = Math.min(parseInt(req.query.limit as string) || 50, 100);

  const where: any = { profileId };
  if (unreadOnly) where.read = false;

  const [notifications, unreadCount] = await Promise.all([
    prisma.notification.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      take: limit,
    }),
    prisma.notification.count({ where: { profileId, read: false } }),
  ]);

  res.json({
    notifications: notifications.map((n) => ({
      id: n.id,
      type: n.type,
      message: n.message,
      linkUrl: n.linkUrl,
      read: n.read,
      createdAt: n.createdAt.toISOString(),
    })),
    unreadCount,
  });
});

/**
 * GET /api/notifications/count
 * Quick unread count endpoint (lightweight polling fallback).
 */
router.get('/count', requireAuth, async (req, res) => {
  const profileId = req.tokenPayload!.profileId;
  if (!profileId) {
    res.json({ unreadCount: 0 });
    return;
  }

  const unreadCount = await prisma.notification.count({
    where: { profileId, read: false },
  });

  res.json({ unreadCount });
});

/**
 * POST /api/notifications/read
 * Body: { ids: number[] } — mark specific notifications as read.
 * Or { all: true } — mark all as read.
 */
router.post('/read', requireAuth, async (req, res) => {
  const profileId = req.tokenPayload!.profileId;
  if (!profileId) {
    res.status(403).json({ error: 'No profile linked' });
    return;
  }

  const { ids, all } = req.body;

  if (all === true) {
    await prisma.notification.updateMany({
      where: { profileId, read: false },
      data: { read: true },
    });
    res.json({ ok: true });
    return;
  }

  if (Array.isArray(ids) && ids.length > 0) {
    await prisma.notification.updateMany({
      where: { id: { in: ids }, profileId },
      data: { read: true },
    });
    res.json({ ok: true });
    return;
  }

  res.status(400).json({ error: 'Provide ids array or all: true' });
});

export { router as notificationsRouter };
