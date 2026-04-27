import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * POST /api/report
 * Body: { postId?: number, commentId?: number, reason: string }
 */
router.post('/', requireAuth, apiLimiter, async (req, res) => {
  const { postId, commentId, reason } = req.body;

  if (!reason || typeof reason !== 'string') {
    res.status(400).json({ error: 'Reason required' });
    return;
  }

  if (!postId && !commentId) {
    res.status(400).json({ error: 'postId or commentId required' });
    return;
  }

  const report = await prisma.report.create({
    data: {
      postId: postId || null,
      commentId: commentId || null,
      reason: reason.slice(0, 1000),
    },
  });

  res.status(201).json({ id: report.id, message: 'Report submitted' });
});

export default router;
