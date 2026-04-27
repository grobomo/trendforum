import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * POST /api/vote
 * Body: { postId?: number, commentId?: number, value: 1 | -1 }
 *
 * Voting is per-session (keyed by JWT jti).
 * Re-voting with the same value removes the vote (toggle).
 * Re-voting with opposite value changes it.
 * Returns the new score after the operation.
 */
router.post('/', requireAuth, apiLimiter, async (req, res) => {
  const { postId, commentId, value } = req.body;
  const jti = req.tokenPayload!.jti;

  if (value !== 1 && value !== -1) {
    res.status(400).json({ error: 'value must be 1 or -1' });
    return;
  }

  if (!postId && !commentId) {
    res.status(400).json({ error: 'postId or commentId required' });
    return;
  }

  if (postId && commentId) {
    res.status(400).json({ error: 'Vote on either a post or comment, not both' });
    return;
  }

  try {
    if (postId) {
      const existing = await prisma.vote.findUnique({
        where: { tokenJti_postId: { tokenJti: jti, postId } },
      });

      if (existing) {
        if (existing.value === value) {
          await prisma.vote.delete({ where: { id: existing.id } });
          const score = await updatePostScore(postId);
          res.json({ action: 'removed', postId, voted: null, score });
          return;
        } else {
          await prisma.vote.update({ where: { id: existing.id }, data: { value } });
          const score = await updatePostScore(postId);
          res.json({ action: 'changed', postId, voted: value, score });
          return;
        }
      }

      await prisma.vote.create({ data: { tokenJti: jti, postId, value } });
      const score = await updatePostScore(postId);
      res.json({ action: 'voted', postId, voted: value, score });
    } else {
      const existing = await prisma.vote.findUnique({
        where: { tokenJti_commentId: { tokenJti: jti, commentId } },
      });

      if (existing) {
        if (existing.value === value) {
          await prisma.vote.delete({ where: { id: existing.id } });
          const score = await updateCommentScore(commentId);
          res.json({ action: 'removed', commentId, voted: null, score });
          return;
        } else {
          await prisma.vote.update({ where: { id: existing.id }, data: { value } });
          const score = await updateCommentScore(commentId);
          res.json({ action: 'changed', commentId, voted: value, score });
          return;
        }
      }

      await prisma.vote.create({ data: { tokenJti: jti, commentId, value } });
      const score = await updateCommentScore(commentId);
      res.json({ action: 'voted', commentId, voted: value, score });
    }
  } catch (err: any) {
    res.status(500).json({ error: 'Vote failed' });
  }
});

async function updatePostScore(postId: number): Promise<number> {
  const votes = await prisma.vote.findMany({ where: { postId } });
  const score = votes.reduce((sum, v) => sum + v.value, 0);
  await prisma.post.update({ where: { id: postId }, data: { score } });
  return score;
}

async function updateCommentScore(commentId: number): Promise<number> {
  const votes = await prisma.vote.findMany({ where: { commentId } });
  const score = votes.reduce((sum, v) => sum + v.value, 0);
  await prisma.comment.update({ where: { id: commentId }, data: { score } });
  return score;
}

export default router;
