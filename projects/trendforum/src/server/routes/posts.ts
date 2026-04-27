import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';
import { hotScore } from '../scoring.js';

const prisma = new PrismaClient();

// Main posts router — mounted at /api/posts
const router = Router();

// Separate router for subforum-scoped posts — mounted at /api/subforums
const subforumPostsRouter = Router();

/**
 * GET /api/subforums/:slug/posts?sort=hot|new|top&page=1&limit=25
 */
subforumPostsRouter.get('/:slug/posts', requireAuth, apiLimiter, async (req, res) => {
  const { slug } = req.params;
  const sort = (req.query.sort as string) || 'hot';
  const page = Math.max(1, parseInt(req.query.page as string) || 1);
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit as string) || 25));
  const skip = (page - 1) * limit;

  const subforum = await prisma.subforum.findUnique({ where: { slug } });
  if (!subforum) {
    res.status(404).json({ error: 'Subforum not found' });
    return;
  }

  let orderBy: any;
  if (sort === 'new') {
    orderBy = { createdAt: 'desc' as const };
  } else if (sort === 'top') {
    orderBy = { score: 'desc' as const };
  } else {
    orderBy = { createdAt: 'desc' as const };
  }

  const posts = await prisma.post.findMany({
    where: { subforumId: subforum.id },
    orderBy,
    skip: sort === 'hot' ? 0 : skip,
    take: sort === 'hot' ? 200 : limit,
    include: {
      _count: { select: { comments: true } },
      votes: true,
    },
  });

  let result = posts.map((p) => {
    const upvotes = p.votes.filter((v) => v.value > 0).length;
    const downvotes = p.votes.filter((v) => v.value < 0).length;
    return {
      id: p.id,
      title: p.title,
      body: p.body ? (p.body.length > 300 ? p.body.slice(0, 300) + '...' : p.body) : null,
      linkUrl: p.linkUrl,
      score: upvotes - downvotes,
      upvotes,
      downvotes,
      commentCount: p._count.comments,
      createdAt: p.createdAt.toISOString(),
      hotScore: hotScore(upvotes, downvotes, p.createdAt),
      subforumSlug: slug,
      subforumName: subforum.name,
    };
  });

  if (sort === 'hot') {
    result.sort((a, b) => b.hotScore - a.hotScore);
    result = result.slice(skip, skip + limit);
  }

  res.json({
    posts: result,
    page,
    limit,
    subforum: { id: subforum.id, slug, name: subforum.name, description: subforum.description },
  });
});

/**
 * GET /api/posts — Home feed (all subforums)
 */
router.get('/', requireAuth, apiLimiter, async (req, res) => {
  const sort = (req.query.sort as string) || 'hot';
  const page = Math.max(1, parseInt(req.query.page as string) || 1);
  const limit = Math.min(50, Math.max(1, parseInt(req.query.limit as string) || 25));
  const skip = (page - 1) * limit;

  const posts = await prisma.post.findMany({
    orderBy: sort === 'top' ? { score: 'desc' } : { createdAt: 'desc' },
    skip: sort === 'hot' ? 0 : skip,
    take: sort === 'hot' ? 200 : limit,
    include: {
      subforum: true,
      _count: { select: { comments: true } },
      votes: true,
    },
  });

  let result = posts.map((p) => {
    const upvotes = p.votes.filter((v) => v.value > 0).length;
    const downvotes = p.votes.filter((v) => v.value < 0).length;
    return {
      id: p.id,
      title: p.title,
      body: p.body ? (p.body.length > 300 ? p.body.slice(0, 300) + '...' : p.body) : null,
      linkUrl: p.linkUrl,
      score: upvotes - downvotes,
      upvotes,
      downvotes,
      commentCount: p._count.comments,
      createdAt: p.createdAt.toISOString(),
      hotScore: hotScore(upvotes, downvotes, p.createdAt),
      subforumSlug: p.subforum.slug,
      subforumName: p.subforum.name,
    };
  });

  if (sort === 'hot') {
    result.sort((a, b) => b.hotScore - a.hotScore);
    result = result.slice(skip, skip + limit);
  }

  res.json({ posts: result, page, limit });
});

/**
 * GET /api/posts/:id — Single post with full comment tree
 */
router.get('/:id', requireAuth, apiLimiter, async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: 'Invalid post ID' });
    return;
  }

  const post = await prisma.post.findUnique({
    where: { id },
    include: {
      subforum: true,
      votes: true,
      comments: {
        orderBy: { createdAt: 'asc' },
        include: { votes: true },
      },
    },
  });

  if (!post) {
    res.status(404).json({ error: 'Post not found' });
    return;
  }

  const upvotes = post.votes.filter((v) => v.value > 0).length;
  const downvotes = post.votes.filter((v) => v.value < 0).length;

  // Build threaded comment tree
  const commentMap = new Map<number, any>();
  const rootComments: any[] = [];

  for (const c of post.comments) {
    const cup = c.votes.filter((v) => v.value > 0).length;
    const cdn = c.votes.filter((v) => v.value < 0).length;
    const node = {
      id: c.id,
      displayName: c.displayName,
      body: c.body,
      score: cup - cdn,
      createdAt: c.createdAt.toISOString(),
      parentId: c.parentId,
      children: [] as any[],
    };
    commentMap.set(c.id, node);
  }

  for (const node of commentMap.values()) {
    if (node.parentId && commentMap.has(node.parentId)) {
      commentMap.get(node.parentId)!.children.push(node);
    } else {
      rootComments.push(node);
    }
  }

  res.json({
    id: post.id,
    title: post.title,
    body: post.body,
    linkUrl: post.linkUrl,
    score: upvotes - downvotes,
    upvotes,
    downvotes,
    createdAt: post.createdAt.toISOString(),
    subforum: { id: post.subforum.id, slug: post.subforum.slug, name: post.subforum.name },
    comments: rootComments,
    commentCount: post.comments.length,
  });
});

/**
 * POST /api/posts — Create a new post
 */
router.post('/', requireAuth, apiLimiter, async (req, res) => {
  const { subforumId, title, body, linkUrl } = req.body;
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
    data: {
      subforumId,
      title: title.slice(0, 300),
      body: body?.slice(0, 10000) || null,
      linkUrl: linkUrl || null,
    },
  });

  res.status(201).json({ id: post.id, subforumSlug: subforum.slug });
});

export { subforumPostsRouter };
export default router;
