import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAdmin } from '../middleware/requireAuth.js';

const router = Router();

router.get('/reports', requireAdmin, async (_req, res) => {
  const reports = await prisma.report.findMany({
    include: {
      post: { include: { subforum: true } },
      comment: true,
    },
    orderBy: { createdAt: 'desc' },
  });
  res.json(reports);
});

router.post('/action', requireAdmin, async (req, res) => {
  const { action, targetId, targetType, reason } = req.body;

  if (!action || !targetId || !targetType) {
    res.status(400).json({ error: 'action, targetId, and targetType required' });
    return;
  }

  const modAction = await prisma.modAction.create({
    data: { action, targetId, targetType, reason: reason || null },
  });

  if (action === 'remove_post' && targetType === 'post') {
    await prisma.vote.deleteMany({ where: { postId: targetId } });
    await prisma.vote.deleteMany({ where: { comment: { postId: targetId } } });
    await prisma.report.deleteMany({ where: { postId: targetId } });
    await prisma.report.deleteMany({ where: { comment: { postId: targetId } } });
    await prisma.comment.deleteMany({ where: { postId: targetId } });
    await prisma.post.delete({ where: { id: targetId } });
  } else if (action === 'remove_comment' && targetType === 'comment') {
    await prisma.vote.deleteMany({ where: { commentId: targetId } });
    await prisma.report.deleteMany({ where: { commentId: targetId } });
    await prisma.comment.deleteMany({ where: { parentId: targetId } });
    await prisma.comment.delete({ where: { id: targetId } });
  }

  res.json(modAction);
});

export { router as modRouter };
