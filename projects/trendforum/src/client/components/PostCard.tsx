import React from 'react';
import { Link } from 'react-router-dom';
import VoteButton from './VoteButton';

interface Props {
  post: any;
  showSubforum?: boolean;
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PostCard({ post, showSubforum = true }: Props) {
  return (
    <div className="bg-forum-card border border-forum-border rounded-lg hover:border-forum-muted/30 transition flex">
      {/* Vote column */}
      <div className="flex flex-col items-center py-3 px-2 bg-forum-bg/50 rounded-l-lg">
        <VoteButton postId={post.id} currentScore={post.score} />
      </div>

      {/* Content */}
      <div className="flex-1 py-3 pr-4 min-w-0">
        {/* Meta line */}
        <div className="flex items-center gap-2 text-xs text-forum-muted mb-1">
          {showSubforum && post.subforum && (
            <>
              <Link
                to={`/t/${post.subforum.slug}`}
                className="font-bold text-white hover:text-forum-accent transition"
              >
                t/{post.subforum.slug}
              </Link>
              <span>·</span>
            </>
          )}
          <span>{timeAgo(post.createdAt)}</span>
        </div>

        {/* Title */}
        <Link
          to={`/t/${post.subforum?.slug || 'general'}/post/${post.id}`}
          className="text-lg font-medium text-white hover:text-forum-accent transition leading-snug"
        >
          {post.title}
        </Link>

        {/* Body preview */}
        {post.body && (
          <p className="text-sm text-forum-muted mt-1 line-clamp-2">
            {post.body}
          </p>
        )}

        {/* Link */}
        {post.linkUrl && (
          <a
            href={post.linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-400 hover:underline mt-1 inline-block"
          >
            🔗 {new URL(post.linkUrl).hostname}
          </a>
        )}

        {/* Footer */}
        <div className="flex items-center gap-4 mt-2 text-xs text-forum-muted">
          <Link
            to={`/t/${post.subforum?.slug || 'general'}/post/${post.id}`}
            className="hover:text-white transition"
          >
            💬 {post._count?.comments || 0} comments
          </Link>
        </div>
      </div>
    </div>
  );
}
