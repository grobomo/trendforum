import { Router } from 'express';
import { prisma } from '../db.js';

const router = Router();

router.get('/search', async (req, res) => {
  const { q, page = '1' } = req.query;

  if (!q || typeof q !== 'string' || q.trim().length < 2) {
    res.status(400).json({ error: 'Query must be at least 2 characters' });
    return;
  }

  const pageNum = parseInt(page as string, 10) || 1;
  const perPage = 25;
  const term = `%${q.trim()}%`;

  const posts = await prisma.post.findMany({
    where: {
      OR: [
        { title: { contains: q.trim() } },
        { body: { contains: q.trim() } },
      ],
    },
    include: { subforum: true, _count: { select: { comments: true } } },
    orderBy: { createdAt: 'desc' },
    skip: (pageNum - 1) * perPage,
    take: perPage,
  });

  res.json(posts);
});

export { router as searchRouter };
