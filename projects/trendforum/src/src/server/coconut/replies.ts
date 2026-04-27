import Anthropic from '@anthropic-ai/sdk';
import type { Post, Comment, Subforum } from '@prisma/client';

type PostWithSubforum = Post & { subforum: Subforum };
type CommentWithPost = Comment & { post: PostWithSubforum };

// ---------------------------------------------------------------------------
// Template-based fallback replies (kept for graceful degradation)
// ---------------------------------------------------------------------------

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

const SUBFORUM_REPLIES: Record<string, string[]> = {
  engineering: [
    'Love the technical deep-dive here.',
    'Solid engineering discussion. What\'s the tradeoff analysis?',
    'Has anyone benchmarked this approach?',
  ],
  'product-feedback': [
    'Great feedback — this is exactly what product needs to hear.',
    'Seconding this. Would love to see it prioritized.',
  ],
  random: [
    'Ha! This made my day.',
    'Quality shitpost. A+.',
  ],
};

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ---------------------------------------------------------------------------
// LLM helpers
// ---------------------------------------------------------------------------

const COCONUT_SYSTEM_PROMPT =
  'You are Coconut, a friendly forum bot. Reply briefly and naturally to forum posts. Keep replies under 2 sentences. Be warm, witty, and genuinely engage with the topic.';

const MODEL = 'claude-3-5-haiku-20241022';

let anthropicClient: Anthropic | null = null;

/** Whether the LLM path is enabled (API key present + COCONUT_LLM truthy). */
export function isLLMEnabled(): boolean {
  const key = process.env.ANTHROPIC_API_KEY;
  const flag = process.env.COCONUT_LLM;
  return !!key && !!flag;
}

function getClient(): Anthropic | null {
  if (!isLLMEnabled()) return null;
  if (!anthropicClient) {
    anthropicClient = new Anthropic(); // reads ANTHROPIC_API_KEY from env
  }
  return anthropicClient;
}

async function callLLM(userPrompt: string): Promise<string | null> {
  const client = getClient();
  if (!client) return null;

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 128,
    system: COCONUT_SYSTEM_PROMPT,
    messages: [{ role: 'user', content: userPrompt }],
  });

  const textBlock = response.content.find((b) => b.type === 'text');
  return textBlock ? textBlock.text.trim() : null;
}

// ---------------------------------------------------------------------------
// Template-based fallback generators
// ---------------------------------------------------------------------------

function templatePostReply(post: PostWithSubforum): string {
  const subforumReplies = SUBFORUM_REPLIES[post.subforum.slug];
  if (subforumReplies && Math.random() < 0.4) {
    return pickRandom(subforumReplies);
  }
  return pickRandom(POST_REPLIES);
}

function templateCommentReply(comment: CommentWithPost): string {
  const subforumReplies = SUBFORUM_REPLIES[comment.post.subforum.slug];
  if (subforumReplies && Math.random() < 0.3) {
    return pickRandom(subforumReplies);
  }
  return pickRandom(COMMENT_REPLIES);
}

// ---------------------------------------------------------------------------
// Public API (now async, with graceful fallback)
// ---------------------------------------------------------------------------

export async function generatePostReply(post: PostWithSubforum): Promise<string> {
  if (isLLMEnabled()) {
    try {
      const prompt = `You are replying to a new post in the "${post.subforum.name}" subforum.\n\nTitle: ${post.title}\n\nBody:\n${post.body ?? '(no body)'}`;
      const reply = await callLLM(prompt);
      if (reply) return reply;
    } catch (err) {
      console.error('[Coconut] LLM call failed for post reply, falling back to template:', err);
    }
  }
  return templatePostReply(post);
}

export async function generateCommentReply(comment: CommentWithPost): Promise<string> {
  if (isLLMEnabled()) {
    try {
      const prompt = `You are replying to a comment in the "${comment.post.subforum.name}" subforum.\n\nOriginal post title: ${comment.post.title}\n\nComment by ${comment.displayName}:\n${comment.body}`;
      const reply = await callLLM(prompt);
      if (reply) return reply;
    } catch (err) {
      console.error('[Coconut] LLM call failed for comment reply, falling back to template:', err);
    }
  }
  return templateCommentReply(comment);
}

export function shouldReply(): boolean {
  return Math.random() < 0.6;
}
