import { Link } from 'react-router-dom';
import { VoteButton } from './VoteButton';
import { formatTimeAgo } from '../lib/time';
import { Markdown } from './Markdown';

export function PostCard({ post }: { post: any }) {
  return (
    <div className="bg-card border border-border rounded-md mb-2 flex hover:border-border-hover transition">
      <VoteButton score={post.score} postId={post.id} />
      <div className="py-1.5 sm:py-2 pr-2 sm:pr-3 flex-1 min-w-0">
        <div className="text-xs text-muted mb-0.5 sm:mb-1">
          <Link to={`/t/${post.subforum.slug}`} className="text-accent hover:underline">
            t/{post.subforum.slug}
          </Link>
          {' '}&middot; {formatTimeAgo(post.createdAt)}
        </div>
        <Link to={`/t/${post.subforum.slug}/post/${post.id}`} className="block">
          <h2 className="text-base sm:text-lg font-medium text-text hover:text-text transition leading-snug">
            {post.title}
          </h2>
          {post.body && (
            <div className="line-clamp-3">
              <Markdown content={post.body} className="text-sm text-muted mt-1" />
            </div>
          )}
          {post.imageUrl && (
            <img src={post.imageUrl} alt="" className="mt-2 max-h-48 rounded border border-border" loading="lazy" />
          )}
          {post.linkUrl && (
            <span className="text-xs text-blue-400 mt-1 block truncate">{post.linkUrl}</span>
          )}
        </Link>
        <div className="text-xs text-muted mt-2">
          <Link
            to={`/t/${post.subforum.slug}/post/${post.id}`}
            className="hover:text-text transition"
          >
            {post._count?.comments || 0} comments
          </Link>
        </div>
      </div>
    </div>
  );
}
