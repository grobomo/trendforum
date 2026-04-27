import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import PostCard from './PostCard';
import SortTabs from './SortTabs';
import { usePosts } from '../hooks/usePosts';

export default function HomeFeed() {
  const [sort, setSort] = useState('hot');
  const { data, loading, error } = usePosts(undefined, sort);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <SortTabs sort={sort} onSort={setSort} />
      </div>

      {loading && (
        <div className="text-center py-12 text-forum-muted">Loading...</div>
      )}

      {error && (
        <div className="text-center py-12 text-red-400">{error}</div>
      )}

      {data && data.posts.length === 0 && (
        <div className="text-center py-12">
          <p className="text-forum-muted text-lg">No posts yet.</p>
          <p className="text-forum-muted mt-2">Be the first — pick a subforum and start a conversation.</p>
        </div>
      )}

      <div className="space-y-3">
        {data?.posts.map((post) => (
          <PostCard key={post.id} post={post} showSubforum={true} />
        ))}
      </div>

      {data && data.totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          {Array.from({ length: data.totalPages }, (_, i) => (
            <button
              key={i}
              className={`px-3 py-1 rounded text-sm ${
                data.page === i + 1
                  ? 'bg-forum-accent text-white'
                  : 'bg-forum-card text-forum-muted hover:text-white'
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
