import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * GET /api/subforums
 * List all subforums with post counts.
 */
router.get('/', requireAuth, apiLimiter, async (_req, res) => {
  const subforums = await prisma.subforum.findMany({
    orderBy: { name: 'asc' },
    include: {
      _count: { select: { posts: true } },
    },
  });

  res.json(subforums.map((sf) => ({
    id: sf.id,
    slug: sf.slug,
    name: sf.name,
    description: sf.description,
    postCount: sf._count.posts,
  })));
});

export default router;
