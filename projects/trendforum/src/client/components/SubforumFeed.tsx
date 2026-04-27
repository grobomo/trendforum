import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { Pagination } from './Pagination';
import { SortTabs } from './SortTabs';
import { useWebSocket } from '../hooks/useWebSocket';

const PER_PAGE = 25;

export function SubforumFeed() {
  const { slug } = useParams<{ slug: string }>();
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';
  const page = parseInt(searchParams.get('page') || '1', 10);
  const [newPostCount, setNewPostCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const loadPosts = useCallback(() => {
    if (slug) {
      api.posts.bySubforum(slug, sort, page).then((data) => {
        setPosts(data);
        setHasMore(data.length >= PER_PAGE);
      }).catch(() => {});
    }
  }, [slug, sort, page]);

  useEffect(() => {
    loadPosts();
    setNewPostCount(0);
  }, [loadPosts]);

  useWebSocket(useCallback((event) => {
    if (event.type === 'new_post' && event.subforumSlug === slug) {
      setNewPostCount((n) => n + 1);
    }
    if (event.type === 'vote_update' && event.postId) {
      setPosts((prev) =>
        prev.map((p) => p.id === event.postId ? { ...p, score: event.score } : p)
      );
    }
  }, [slug]));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold text-[#e0e0e0]">t/{slug}</h1>
        <Link
          to={`/t/${slug}/submit`}
          className="px-3 py-1 bg-[#D5232F] text-white rounded text-sm hover:bg-red-700 transition"
        >
          New Post
        </Link>
      </div>
      <SortTabs current={sort} />
      {newPostCount > 0 && (
        <button
          onClick={() => { loadPosts(); setNewPostCount(0); }}
          className="w-full py-2 mb-3 bg-[#2a2a4a] border border-[#D5232F] rounded text-sm text-[#D5232F] hover:bg-[#D5232F] hover:text-white transition"
        >
          {newPostCount} new {newPostCount === 1 ? 'post' : 'posts'} — click to refresh
        </button>
      )}
      {posts.length === 0 ? (
        <div className="text-center text-[#8888aa] py-12">No posts in this subforum yet.</div>
      ) : (
        <>
          {posts.map((post) => <PostCard key={post.id} post={post} />)}
          <Pagination hasMore={hasMore} />
        </>
      )}
    </div>
  );
}
