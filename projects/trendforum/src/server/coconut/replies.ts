import { execFile } from 'child_process';
import { writeFileSync, unlinkSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import crypto from 'crypto';
import type { Post, Comment, Subforum } from '@prisma/client';

type PostWithSubforum = Post & { subforum: Subforum };
type CommentWithPost = Comment & { post: PostWithSubforum };

const SYSTEM_PROMPT = `You are Coconut, a friendly community member on an anonymous forum called TrendForum.
Rules:
- Write short, natural replies (1-3 sentences max)
- Match the tone of the subforum and conversation
- Be genuine and conversational, not corporate or generic
- Sometimes ask a follow-up question
- Never mention being a bot, AI, or automated
- Never use emojis excessively (0-1 per reply max)
- Respond to the actual content, not just with platitudes
- Output ONLY your reply text, nothing else`;

let claudeAvailable: boolean | null = null;

function checkClaudeAvailable(): boolean {
  if (claudeAvailable !== null) return claudeAvailable;
  try {
    const { execFileSync } = require('child_process');
    execFileSync('claude', ['--version'], { timeout: 5000, stdio: 'pipe' });
    claudeAvailable = true;
  } catch {
    claudeAvailable = false;
    console.log('[Coconut] claude CLI not found — using template replies');
  }
  return claudeAvailable;
}

function callClaude(userMessage: string): Promise<string> {
  return new Promise((resolve) => {
    const promptFile = join(tmpdir(), `coconut-${crypto.randomBytes(4).toString('hex')}.txt`);
    const fullPrompt = `${SYSTEM_PROMPT}\n\n${userMessage}`;
    writeFileSync(promptFile, fullPrompt);

    execFile('claude', ['-p', '--dangerously-skip-permissions'], {
      timeout: 30000,
      maxBuffer: 1024 * 64,
    }, (err, stdout, stderr) => {
      try { unlinkSync(promptFile); } catch {}
      if (err) {
        console.error('[Coconut] claude -p error:', err.message);
        resolve('');
        return;
      }
      resolve(stdout.trim());
    }).stdin?.end(fullPrompt);
  });
}

// --- Template fallbacks (used when claude CLI is not available) ---

const POST_REPLIES = [
  'Welcome to the conversation! Great topic.',
  'Interesting point — curious what others think about this.',
  'Thanks for posting! This is the kind of discussion we need.',
  'Good stuff. Following this thread.',
  'Nice one! Looking forward to the replies here.',
];

const COMMENT_REPLIES = [
  'Good take. I see where you\'re coming from.',
  'That\'s a solid point.',
  'Interesting perspective — thanks for sharing.',
  'Appreciate the input here.',
  'Well said.',
];

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export async function generatePostReply(post: PostWithSubforum): Promise<string> {
  if (checkClaudeAvailable()) {
    const prompt = `Reply to this new post in the "${post.subforum.name}" subforum:\n\nTitle: ${post.title}${post.body ? `\n\n${post.body}` : ''}`;
    const reply = await callClaude(prompt);
    if (reply) return reply;
  }
  return pickRandom(POST_REPLIES);
}

export async function generateCommentReply(comment: CommentWithPost): Promise<string> {
  if (checkClaudeAvailable()) {
    const prompt = `Reply to this comment on a post titled "${comment.post.title}" in the "${comment.post.subforum.name}" subforum:\n\nComment: ${comment.body}`;
    const reply = await callClaude(prompt);
    if (reply) return reply;
  }
  return pickRandom(COMMENT_REPLIES);
}

export function shouldReply(): boolean {
  return Math.random() < 0.6;
}
