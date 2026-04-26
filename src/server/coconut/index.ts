import { prisma } from '../db.js';
import { generatePostReply, generateCommentReply, shouldReply } from './replies.js';

const DISPLAY_NAME = 'Coconut';
const DEFAULT_POLL_INTERVAL_MS = parseInt(process.env.COCONUT_POLL_MS || '30000', 10);

export class CoconutBot {
  private interval: ReturnType<typeof setInterval> | null = null;
  private lastSeen: Date;
  private pollIntervalMs: number;
  private processedPosts = new Set<number>();
  private processedComments = new Set<number>();

  constructor(pollIntervalMs = DEFAULT_POLL_INTERVAL_MS) {
    this.lastSeen = new Date();
    this.pollIntervalMs = pollIntervalMs;
  }

  get running(): boolean {
    return this.interval !== null;
  }

  start(): void {
    if (this.interval) return;
    this.lastSeen = new Date();
    this.processedPosts.clear();
    this.processedComments.clear();
    this.interval = setInterval(() => this.poll(), this.pollIntervalMs);
    console.log(`[Coconut] Started — polling every ${this.pollIntervalMs / 1000}s`);
  }

  stop(): void {
    if (!this.interval) return;
    clearInterval(this.interval);
    this.interval = null;
    console.log('[Coconut] Stopped');
  }

  status(): { running: boolean; lastSeen: string; stats: { postsProcessed: number; commentsProcessed: number } } {
    return {
      running: this.running,
      lastSeen: this.lastSeen.toISOString(),
      stats: {
        postsProcessed: this.processedPosts.size,
        commentsProcessed: this.processedComments.size,
      },
    };
  }

  private async poll(): Promise<void> {
    try {
      const since = this.lastSeen;
      const now = new Date();

      const [posts, comments] = await Promise.all([
        prisma.post.findMany({
          where: { createdAt: { gt: since } },
          include: { subforum: true },
          orderBy: { createdAt: 'asc' },
        }),
        prisma.comment.findMany({
          where: {
            createdAt: { gt: since },
            displayName: { not: DISPLAY_NAME },
          },
          include: { post: { include: { subforum: true } } },
          orderBy: { createdAt: 'asc' },
        }),
      ]);

      for (const post of posts) {
        if (this.processedPosts.has(post.id)) continue;
        this.processedPosts.add(post.id);

        if (shouldReply()) {
          const body = await generatePostReply(post);
          await prisma.comment.create({
            data: {
              postId: post.id,
              body,
              displayName: DISPLAY_NAME,
            },
          });
          console.log(`[Coconut] Replied to post #${post.id}`);
        }
      }

      for (const comment of comments) {
        if (this.processedComments.has(comment.id)) continue;
        this.processedComments.add(comment.id);

        if (shouldReply()) {
          const body = await generateCommentReply(comment);
          await prisma.comment.create({
            data: {
              postId: comment.postId,
              parentId: comment.id,
              body,
              displayName: DISPLAY_NAME,
            },
          });
          console.log(`[Coconut] Replied to comment #${comment.id} on post #${comment.postId}`);
        }
      }

      this.lastSeen = now;
    } catch (err) {
      console.error('[Coconut] Poll error:', err);
    }
  }
}

export const coconutBot = new CoconutBot();
