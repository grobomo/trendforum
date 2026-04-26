import { Link } from 'react-router-dom';
import { VoteButton } from './VoteButton';
import { formatTimeAgo } from '../lib/time';

export function PostCard({ post }: { post: any }) {
  return (
    <div className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md mb-2 flex hover:border-[#3a3a5a] transition">
      <VoteButton score={post.score} postId={post.id} />
      <div className="py-1.5 sm:py-2 pr-2 sm:pr-3 flex-1 min-w-0">
        <div className="text-xs text-[#8888aa] mb-0.5 sm:mb-1">
          <Link to={`/t/${post.subforum.slug}`} className="text-[#D5232F] hover:underline">
            t/{post.subforum.slug}
          </Link>
          {' '}&middot; {formatTimeAgo(post.createdAt)}
        </div>
        <Link to={`/t/${post.subforum.slug}/post/${post.id}`} className="block">
          <h2 className="text-base sm:text-lg font-medium text-[#e0e0e0] hover:text-white transition leading-snug">
            {post.title}
          </h2>
          {post.body && (
            <p className="text-sm text-[#aaaacc] mt-1 line-clamp-3">{post.body}</p>
          )}
          {post.linkUrl && (
            <span className="text-xs text-blue-400 mt-1 block truncate">{post.linkUrl}</span>
          )}
        </Link>
        <div className="text-xs text-[#8888aa] mt-2">
          <Link
            to={`/t/${post.subforum.slug}/post/${post.id}`}
            className="hover:text-white transition"
          >
            {post._count?.comments || 0} comments
          </Link>
        </div>
      </div>
    </div>
  );
}
