import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { VoteButton } from './VoteButton';
import { CommentTree } from './CommentTree';
import { formatTimeAgo } from '../lib/time';

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

  if (!post) return <div className="text-[#8888aa] py-8 text-center">Loading...</div>;

  return (
    <div>
      <div className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md flex">
        <VoteButton score={post.score} postId={post.id} />
        <div className="py-3 pr-4 flex-1">
          <div className="text-xs text-[#8888aa] mb-1">
            <Link to={`/t/${slug}`} className="text-[#D5232F] hover:underline">
              t/{slug}
            </Link>
            {' '}&middot; {formatTimeAgo(post.createdAt)}
          </div>
          <h1 className="text-xl font-bold text-[#e0e0e0]">{post.title}</h1>
          {post.body && (
            <p className="text-[#aaaacc] mt-2 whitespace-pre-wrap">{post.body}</p>
          )}
          {post.imageUrl && (
            <img src={post.imageUrl} alt="" className="mt-3 max-w-full rounded border border-[#2a2a4a]" loading="lazy" />
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
        className="mt-4 bg-[#1e1e3a] border border-[#2a2a4a] rounded-md p-4"
      >
        <textarea
          value={commentBody}
          onChange={(e) => setCommentBody(e.target.value)}
          placeholder="What are your thoughts?"
          className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-3 text-[#e0e0e0] placeholder-[#666688] resize-y min-h-[80px] focus:outline-none focus:border-[#D5232F] transition"
          rows={3}
        />
        <div className="mt-2 flex justify-end">
          <button
            type="submit"
            disabled={submitting || !commentBody.trim()}
            className="px-4 py-1.5 bg-[#D5232F] text-white rounded text-sm hover:bg-red-700 disabled:opacity-50 transition"
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
