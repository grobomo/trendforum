import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { Pagination } from './Pagination';

const PER_PAGE = 25;

export function SearchResults() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const q = searchParams.get('q') || '';
  const page = parseInt(searchParams.get('page') || '1', 10);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    if (q.length >= 2) {
      setLoading(true);
      api.search.query(q, page).then((data) => {
        setPosts(data);
        setHasMore(data.length >= PER_PAGE);
      }).catch(() => {}).finally(() => setLoading(false));
    }
  }, [q, page]);

  return (
    <div>
      <h1 className="text-xl font-bold text-[#e0e0e0] mb-4">
        Search results for "{q}"
      </h1>
      {loading ? (
        <div className="text-[#8888aa] py-8 text-center">Searching...</div>
      ) : posts.length === 0 ? (
        <div className="text-[#8888aa] py-8 text-center">No posts found.</div>
      ) : (
        <>
          {posts.map((post) => <PostCard key={post.id} post={post} />)}
          <Pagination hasMore={hasMore} />
        </>
      )}
    </div>
  );
}
