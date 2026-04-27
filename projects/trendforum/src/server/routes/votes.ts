import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';
import { broadcast } from '../ws.js';

const router = Router();

router.post('/vote', requireAuth, async (req, res) => {
  const { postId, commentId, value } = req.body;
  const tokenJti = req.token!.jti;

  if (value !== 1 && value !== -1) {
    res.status(400).json({ error: 'Value must be 1 or -1' });
    return;
  }

  if (!postId && !commentId) {
    res.status(400).json({ error: 'postId or commentId required' });
    return;
  }

  try {
    if (postId) {
      const existing = await prisma.vote.findUnique({
        where: { tokenJti_postId: { tokenJti, postId } },
      });

      if (existing) {
        if (existing.value === value) {
          await prisma.vote.delete({ where: { id: existing.id } });
          const updated = await prisma.post.update({ where: { id: postId }, data: { score: { decrement: value } } });
          broadcast({ type: 'vote_update', postId, score: updated.score });
          res.json({ voted: null });
          return;
        }
        await prisma.vote.update({ where: { id: existing.id }, data: { value } });
        const updated = await prisma.post.update({ where: { id: postId }, data: { score: { increment: value * 2 } } });
        broadcast({ type: 'vote_update', postId, score: updated.score });
        res.json({ voted: value });
        return;
      }

      await prisma.vote.create({ data: { tokenJti, postId, value } });
      const updated = await prisma.post.update({ where: { id: postId }, data: { score: { increment: value } } });
      broadcast({ type: 'vote_update', postId, score: updated.score });
      res.json({ voted: value });
      return;
    }

    if (commentId) {
      const existing = await prisma.vote.findUnique({
        where: { tokenJti_commentId: { tokenJti, commentId } },
      });

      if (existing) {
        if (existing.value === value) {
          await prisma.vote.delete({ where: { id: existing.id } });
          const updated = await prisma.comment.update({ where: { id: commentId }, data: { score: { decrement: value } } });
          broadcast({ type: 'vote_update', commentId, score: updated.score });
          res.json({ voted: null });
          return;
        }
        await prisma.vote.update({ where: { id: existing.id }, data: { value } });
        const updated = await prisma.comment.update({ where: { id: commentId }, data: { score: { increment: value * 2 } } });
        broadcast({ type: 'vote_update', commentId, score: updated.score });
        res.json({ voted: value });
        return;
      }

      await prisma.vote.create({ data: { tokenJti, commentId, value } });
      const updated = await prisma.comment.update({ where: { id: commentId }, data: { score: { increment: value } } });
      broadcast({ type: 'vote_update', commentId, score: updated.score });
      res.json({ voted: value });
    }
  } catch {
    res.status(400).json({ error: 'Vote failed' });
  }
});

export { router as votesRouter };
