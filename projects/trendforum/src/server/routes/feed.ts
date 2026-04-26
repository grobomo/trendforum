import { Router } from 'express';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/feed', async (req, res) => {
  const { since } = req.query;

  if (!since) {
    res.status(400).json({ error: 'since parameter required (ISO timestamp)' });
    return;
  }

  const sinceDate = new Date(since as string);

  const [posts, comments] = await Promise.all([
    prisma.post.findMany({
      where: { createdAt: { gt: sinceDate } },
      include: { subforum: true },
      orderBy: { createdAt: 'asc' },
    }),
    prisma.comment.findMany({
      where: { createdAt: { gt: sinceDate } },
      include: { post: { include: { subforum: true } } },
      orderBy: { createdAt: 'asc' },
    }),
  ]);

  res.json({ posts, comments });
});

export { router as feedRouter };
