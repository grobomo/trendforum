import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { VoteButton } from './VoteButton';
import { CommentTree } from './CommentTree';
import { formatTimeAgo } from '../lib/time';
import { Markdown } from './Markdown';

export function PostDetail() {
  const { id, slug } = useParams<{ id: string; slug: string }>();
  const [post, setPost] = useState<any>(null);
  const [commentBody, setCommentBody] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadPost = () => {
    if (id) api.posts.get(parseInt(id, 10)).then(setPost).catch(() => {});
  };

  useEffect(loadPost, [id]);

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentBody.trim() || !post) return;
    setSubmitting(true);
    try {
      await api.comments.create(post.id, { body: commentBody });
      setCommentBody('');
      loadPost();
    } finally {
      setSubmitting(false);
    }
  };

  if (!post) return <div className="text-muted py-8 text-center">Loading...</div>;

  return (
    <div>
      <div className="bg-card border border-border rounded-md flex">
        <VoteButton score={post.score} postId={post.id} />
        <div className="py-3 pr-4 flex-1">
          <div className="text-xs text-muted mb-1">
            <Link to={`/t/${slug}`} className="text-accent hover:underline">
              t/{slug}
            </Link>
            {' '}&middot; {formatTimeAgo(post.createdAt)}
          </div>
          <h1 className="text-xl font-bold text-text">{post.title}</h1>
          {post.body && (
            <Markdown content={post.body} className="mt-2 text-muted" />
          )}
          {post.imageUrl && (
            <img src={post.imageUrl} alt="" className="mt-3 max-w-full rounded border border-border" loading="lazy" />
          )}
          {post.linkUrl && (
            <a
              href={post.linkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 text-sm mt-2 block hover:underline"
            >
              {post.linkUrl}
            </a>
          )}
        </div>
      </div>

      <form
        onSubmit={handleComment}
        className="mt-4 bg-card border border-border rounded-md p-4"
      >
        <textarea
          value={commentBody}
          onChange={(e) => setCommentBody(e.target.value)}
          placeholder="What are your thoughts?"
          className="w-full bg-input border border-border rounded p-3 text-text placeholder-dim resize-y min-h-[80px] focus:outline-none focus:border-accent transition"
          rows={3}
        />
        <div className="mt-2 flex justify-end">
          <button
            type="submit"
            disabled={submitting || !commentBody.trim()}
            className="px-4 py-1.5 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50 transition"
          >
            {submitting ? 'Posting...' : 'Comment'}
          </button>
        </div>
      </form>

      <div className="mt-4">
        <CommentTree comments={post.comments} postId={post.id} onReply={loadPost} />
      </div>
    </div>
  );
}
