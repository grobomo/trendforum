import type { Post, Comment, Subforum } from '@prisma/client';

type PostWithSubforum = Post & { subforum: Subforum };
type CommentWithPost = Comment & { post: PostWithSubforum };

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

export function generatePostReply(post: PostWithSubforum): string {
  const subforumReplies = SUBFORUM_REPLIES[post.subforum.slug];
  if (subforumReplies && Math.random() < 0.4) {
    return pickRandom(subforumReplies);
  }
  return pickRandom(POST_REPLIES);
}

export function generateCommentReply(_comment: CommentWithPost): string {
  const subforumReplies = SUBFORUM_REPLIES[_comment.post.subforum.slug];
  if (subforumReplies && Math.random() < 0.3) {
    return pickRandom(subforumReplies);
  }
  return pickRandom(COMMENT_REPLIES);
}

export function shouldReply(): boolean {
  return Math.random() < 0.6;
}
