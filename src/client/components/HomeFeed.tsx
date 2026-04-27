import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { SortTabs } from './SortTabs';
import { useWebSocket } from '../hooks/useWebSocket';

export function HomeFeed() {
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';
  const [newPostCount, setNewPostCount] = useState(0);

  const loadPosts = useCallback(() => {
    api.posts.list(sort).then(setPosts).catch(() => {});
  }, [sort]);

  useEffect(() => {
    loadPosts();
    setNewPostCount(0);
  }, [loadPosts]);

  useWebSocket(useCallback((event) => {
    if (event.type === 'new_post') {
      setNewPostCount((n) => n + 1);
    }
    if (event.type === 'vote_update' && event.postId) {
      setPosts((prev) =>
        prev.map((p) => p.id === event.postId ? { ...p, score: event.score } : p)
      );
    }
  }, []));

  return (
    <div>
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
        <div className="text-center text-[#8888aa] py-12">No posts yet. Be the first!</div>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
    </div>
  );
}
