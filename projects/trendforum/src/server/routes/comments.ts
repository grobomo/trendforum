import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';
import { generateDisplayName } from '../auth.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * POST /api/posts/:id/comments
 * Body: { body: string, parentId?: number }
 * 
 * Display names are generated per-session per-post-tree.
 * Same session commenting on same post gets same display name.
 */
const displayNameCache = new Map<string, string>(); // `${jti}:${postId}` → displayName

router.post('/:postId/comments', requireAuth, apiLimiter, async (req, res) => {
  const postId = parseInt(req.params.postId);
  if (isNaN(postId)) {
    res.status(400).json({ error: 'Invalid post ID' });
    return;
  }

  const { body, parentId } = req.body;
  if (!body || typeof body !== 'string') {
    res.status(400).json({ error: 'Comment body required' });
    return;
  }

  const post = await prisma.post.findUnique({ where: { id: postId } });
  if (!post) {
    res.status(404).json({ error: 'Post not found' });
    return;
  }

  // Validate parentId if provided
  if (parentId !== undefined && parentId !== null) {
    const parent = await prisma.comment.findUnique({ where: { id: parentId } });
    if (!parent || parent.postId !== postId) {
      res.status(400).json({ error: 'Invalid parent comment' });
      return;
    }
  }

  // Get or create display name for this session + post
  const jti = req.tokenPayload!.jti;
  const cacheKey = `${jti}:${postId}`;
  if (!displayNameCache.has(cacheKey)) {
    displayNameCache.set(cacheKey, generateDisplayName());
  }
  const displayName = displayNameCache.get(cacheKey)!;

  const comment = await prisma.comment.create({
    data: {
      postId,
      parentId: parentId || null,
      displayName,
      body: body.slice(0, 5000),
    },
  });

  res.status(201).json(comment);
});

export default router;
