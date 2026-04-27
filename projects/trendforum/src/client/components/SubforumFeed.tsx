import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import PostCard from './PostCard';
import SortTabs from './SortTabs';
import { usePosts } from '../hooks/usePosts';
import { getSubforum } from '../lib/api';

export default function SubforumFeed() {
  const { slug } = useParams<{ slug: string }>();
  const [sort, setSort] = useState('hot');
  const [subforum, setSubforum] = useState<any>(null);
  const { data, loading, error } = usePosts(slug, sort);

  useEffect(() => {
    if (slug) {
      getSubforum(slug).then(setSubforum).catch(console.error);
    }
  }, [slug]);

  return (
    <div>
      {/* Subforum header */}
      {subforum && (
        <div className="bg-forum-card border border-forum-border rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">t/{subforum.slug}</h1>
              {subforum.description && (
                <p className="text-sm text-forum-muted mt-1">{subforum.description}</p>
              )}
            </div>
            <Link
              to={`/t/${slug}/submit`}
              className="px-4 py-2 bg-forum-accent text-white text-sm font-semibold rounded hover:bg-orange-600 transition"
            >
              + New Post
            </Link>
          </div>
        </div>
      )}

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
          <p className="text-forum-muted text-lg">No posts in t/{slug} yet.</p>
          <Link to={`/t/${slug}/submit`} className="text-forum-accent hover:underline">
            Start the conversation →
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {data?.posts.map((post) => (
          <PostCard key={post.id} post={post} showSubforum={false} />
        ))}
      </div>
    </div>
  );
}
