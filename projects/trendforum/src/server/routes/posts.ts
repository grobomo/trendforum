import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';

const router = Router();

function hotScore(score: number, createdAt: Date): number {
  const order = Math.log10(Math.max(Math.abs(score), 1));
  const sign = score > 0 ? 1 : score < 0 ? -1 : 0;
  const seconds = (createdAt.getTime() - new Date('2026-01-01').getTime()) / 1000;
  return sign * order + seconds / 45000;
}

router.get('/subforums/:slug/posts', async (req, res) => {
  const { slug } = req.params;
  const { sort = 'hot', page = '1' } = req.query;
  const pageNum = parseInt(page as string, 10) || 1;
  const perPage = 25;

  const subforum = await prisma.subforum.findUnique({ where: { slug } });
  if (!subforum) {
    res.status(404).json({ error: 'Subforum not found' });
    return;
  }

  const orderBy = sort === 'top' ? { score: 'desc' as const } : { createdAt: 'desc' as const };

  const posts = await prisma.post.findMany({
    where: { subforumId: subforum.id },
    include: { subforum: true, _count: { select: { comments: true } } },
    orderBy,
    skip: (pageNum - 1) * perPage,
    take: perPage,
  });

  if (sort === 'hot') {
    posts.sort((a, b) => hotScore(b.score, b.createdAt) - hotScore(a.score, a.createdAt));
  }

  res.json(posts);
});

router.get('/posts', async (req, res) => {
  const { sort = 'hot', page = '1' } = req.query;
  const pageNum = parseInt(page as string, 10) || 1;
  const perPage = 25;

  const orderBy = sort === 'top' ? { score: 'desc' as const } : { createdAt: 'desc' as const };

  const posts = await prisma.post.findMany({
    include: { subforum: true, _count: { select: { comments: true } } },
    orderBy,
    skip: (pageNum - 1) * perPage,
    take: perPage,
  });

  if (sort === 'hot') {
    posts.sort((a, b) => hotScore(b.score, b.createdAt) - hotScore(a.score, a.createdAt));
  }

  res.json(posts);
});

router.post('/posts', requireAuth, async (req, res) => {
  const { subforumId, title, body, linkUrl, imageUrl } = req.body;

  if (!subforumId || !title) {
    res.status(400).json({ error: 'subforumId and title are required' });
    return;
  }

  const subforum = await prisma.subforum.findUnique({ where: { id: subforumId } });
  if (!subforum) {
    res.status(404).json({ error: 'Subforum not found' });
    return;
  }

  const post = await prisma.post.create({
    data: { subforumId, title, body: body || null, linkUrl: linkUrl || null, imageUrl: imageUrl || null },
    include: { subforum: true },
  });

  res.status(201).json(post);
});

router.get('/posts/:id', async (req, res) => {
  const id = parseInt(req.params.id, 10);

  const post = await prisma.post.findUnique({
    where: { id },
    include: {
      subforum: true,
      comments: { orderBy: { createdAt: 'asc' } },
      _count: { select: { comments: true } },
    },
  });

  if (!post) {
    res.status(404).json({ error: 'Post not found' });
    return;
  }

  res.json(post);
});

export { router as postsRouter };
