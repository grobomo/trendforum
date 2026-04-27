import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * GET /api/feed?since=<ISO timestamp>
 * Returns new posts and comments since the given timestamp.
 * Used by Coconut for polling integration.
 */
router.get('/', requireAuth, async (req, res) => {
  const since = req.query.since as string;
  if (!since) {
    res.status(400).json({ error: 'since parameter required (ISO timestamp)' });
    return;
  }

  const sinceDate = new Date(since);
  if (isNaN(sinceDate.getTime())) {
    res.status(400).json({ error: 'Invalid date format' });
    return;
  }

  const [posts, comments] = await Promise.all([
    prisma.post.findMany({
      where: { createdAt: { gt: sinceDate } },
      orderBy: { createdAt: 'asc' },
      include: { subforum: { select: { slug: true, name: true } } },
    }),
    prisma.comment.findMany({
      where: { createdAt: { gt: sinceDate } },
      orderBy: { createdAt: 'asc' },
      include: { post: { select: { id: true, title: true } } },
    }),
  ]);

  res.json({
    posts: posts.map((p) => ({
      id: p.id,
      title: p.title,
      body: p.body,
      linkUrl: p.linkUrl,
      subforum: p.subforum,
      createdAt: p.createdAt.toISOString(),
    })),
    comments: comments.map((c) => ({
      id: c.id,
      postId: c.postId,
      postTitle: c.post.title,
      displayName: c.displayName,
      body: c.body,
      createdAt: c.createdAt.toISOString(),
    })),
    since: since,
    fetchedAt: new Date().toISOString(),
  });
});

export default router;
