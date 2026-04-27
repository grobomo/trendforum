import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAdmin } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * GET /api/mod/reports — List all reports
 */
router.get('/reports', requireAdmin, apiLimiter, async (_req, res) => {
  const reports = await prisma.report.findMany({
    orderBy: { createdAt: 'desc' },
    take: 50,
    include: {
      post: { select: { id: true, title: true } },
      comment: { select: { id: true, body: true, displayName: true } },
    },
  });
  res.json(reports);
});

/**
 * POST /api/mod/action
 * Body: { action: string, targetId: number, targetType: "post"|"comment", reason?: string }
 */
router.post('/action', requireAdmin, apiLimiter, async (req, res) => {
  const { action, targetId, targetType, reason } = req.body;

  if (!action || !targetId || !targetType) {
    res.status(400).json({ error: 'action, targetId, and targetType required' });
    return;
  }

  if (!['remove_post', 'remove_comment', 'lock_post'].includes(action)) {
    res.status(400).json({ error: 'Invalid action' });
    return;
  }

  // Execute the mod action
  if (action === 'remove_post' && targetType === 'post') {
    await prisma.post.delete({ where: { id: targetId } });
  } else if (action === 'remove_comment' && targetType === 'comment') {
    await prisma.comment.delete({ where: { id: targetId } });
  }
  // lock_post would need a locked field — skipping for MVP

  const modAction = await prisma.modAction.create({
    data: { action, targetId, targetType, reason: reason || null },
  });

  res.json(modAction);
});

export default router;
