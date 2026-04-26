import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';
import { generateDisplayName } from '../auth.js';

const router = Router();

router.post('/posts/:id/comments', requireAuth, async (req, res) => {
  const postId = parseInt(req.params.id as string, 10);
  const { body, parentId } = req.body;

  if (!body || typeof body !== 'string') {
    res.status(400).json({ error: 'Comment body required' });
    return;
  }

  if (body.length > 10000) {
    res.status(400).json({ error: 'Comment must be 10,000 characters or less' });
    return;
  }

  const post = await prisma.post.findUnique({ where: { id: postId } });
  if (!post) {
    res.status(404).json({ error: 'Post not found' });
    return;
  }

  if (parentId) {
    const parent = await prisma.comment.findUnique({ where: { id: parentId } });
    if (!parent || parent.postId !== postId) {
      res.status(400).json({ error: 'Invalid parent comment' });
      return;
    }
  }

  const displayName = generateDisplayName(req.token!.jti, postId, req.token?.pseudonym);

  const comment = await prisma.comment.create({
    data: {
      postId,
      body,
      parentId: parentId || null,
      displayName,
      profileId: req.token?.profileId || null,
    },
  });

  res.status(201).json(comment);
});

export { router as commentsRouter };
