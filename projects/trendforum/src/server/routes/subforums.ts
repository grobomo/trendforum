import { Router } from 'express';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/', async (_req, res) => {
  const subforums = await prisma.subforum.findMany({
    include: { _count: { select: { posts: true } } },
    orderBy: { name: 'asc' },
  });
  res.json(subforums);
});

export { router as subforumsRouter };
