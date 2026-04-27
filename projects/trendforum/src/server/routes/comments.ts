import { Router } from 'express';
import { prisma } from '../db.js';
import { requireAuth } from '../middleware/requireAuth.js';
import { apiLimiter } from '../middleware/rateLimit.js';
import { generateDisplayName } from '../auth.js';
import { broadcast, sendToProfile } from '../ws.js';
const router = Router();

/**
 * POST /api/posts/:id/comments
 * Body: { body: string, parentId?: number }
 * 
 * If the user has a profile (profileId in JWT), use their username as displayName.
 * Otherwise, generate a random per-session per-post-tree display name.
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

  // Determine display name and profileId
  let displayName: string;
  let profileId: number | null = null;

  const tokenProfileId = req.tokenPayload!.profileId;
  if (tokenProfileId) {
    // User has a profile — look up their username
    const profile = await prisma.profile.findUnique({ where: { id: tokenProfileId } });
    if (profile) {
      displayName = profile.username;
      profileId = profile.id;
    } else {
      // Profile not found (deleted?), fall back to anonymous
      const jti = req.tokenPayload!.jti;
      const cacheKey = `${jti}:${postId}`;
      if (!displayNameCache.has(cacheKey)) {
        displayNameCache.set(cacheKey, generateDisplayName());
      }
      displayName = displayNameCache.get(cacheKey)!;
    }
  } else {
    // Anonymous user — generate random display name per session+post
    const jti = req.tokenPayload!.jti;
    const cacheKey = `${jti}:${postId}`;
    if (!displayNameCache.has(cacheKey)) {
      displayNameCache.set(cacheKey, generateDisplayName());
    }
    displayName = displayNameCache.get(cacheKey)!;
  }

  const comment = await prisma.comment.create({
    data: {
      postId,
      parentId: parentId || null,
      displayName,
      profileId,
      body: body.slice(0, 5000),
    },
  });

  broadcast({ type: 'new_comment', postId, commentId: comment.id });

  // --- Generate notification for parent comment author ---
  if (parentId) {
    try {
      const parentComment = await prisma.comment.findUnique({ where: { id: parentId } });
      // Only notify if parent has a profile AND it's not the same user replying to themselves
      if (parentComment?.profileId && parentComment.profileId !== profileId) {
        const post2 = await prisma.post.findUnique({
          where: { id: postId },
          include: { subforum: { select: { slug: true } } },
        });
        const slug = post2?.subforum?.slug || 'general';
        const linkUrl = `/t/${slug}/post/${postId}`;
        const truncBody = body.length > 80 ? body.slice(0, 80) + '…' : body;
        const message = `${displayName} replied to your comment: "${truncBody}"`;

        const notification = await prisma.notification.create({
          data: {
            profileId: parentComment.profileId,
            type: 'reply',
            message,
            linkUrl,
          },
        });

        sendToProfile(parentComment.profileId, {
          type: 'notification',
          profileId: parentComment.profileId,
          notification: {
            id: notification.id,
            type: notification.type,
            message: notification.message,
            linkUrl: notification.linkUrl,
            createdAt: notification.createdAt.toISOString(),
          },
        });
      }
    } catch {
      // Non-critical — don't fail the comment creation
    }
  }

  res.status(201).json(comment);
});

export default router;
