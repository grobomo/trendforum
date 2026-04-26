import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';

const router = Router();

router.post('/report', requireAuth, async (req, res) => {
  const { postId, commentId, reason } = req.body;

  if (!reason || typeof reason !== 'string') {
    res.status(400).json({ error: 'Reason required' });
    return;
  }

  if (reason.length > 1000) {
    res.status(400).json({ error: 'Reason must be 1,000 characters or less' });
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
      reason,
    },
  });

  res.status(201).json(report);
});

export { router as reportsRouter };
