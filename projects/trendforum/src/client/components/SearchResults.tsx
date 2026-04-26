import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';

export function SearchResults() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const q = searchParams.get('q') || '';

  useEffect(() => {
    if (q.length >= 2) {
      setLoading(true);
      api.search.query(q).then(setPosts).catch(() => {}).finally(() => setLoading(false));
    }
  }, [q]);

  return (
    <div>
      <h1 className="text-xl font-bold text-text mb-4">
        Search results for "{q}"
      </h1>
      {loading ? (
        <div className="text-muted py-8 text-center">Searching...</div>
      ) : posts.length === 0 ? (
        <div className="text-muted py-8 text-center">No posts found.</div>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
    </div>
  );
}
