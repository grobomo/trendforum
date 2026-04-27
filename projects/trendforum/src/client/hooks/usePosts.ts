import { useState, useEffect, useCallback } from 'react';
import { getAllPosts, getSubforumPosts, PostsResponse } from '../lib/api';

export function usePosts(slug?: string, sort = 'hot') {
  const [data, setData] = useState<PostsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = slug
        ? await getSubforumPosts(slug, sort, page)
        : await getAllPosts(sort, page);
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [slug, sort, page]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  return { data, loading, error, page, setPage, refetch: fetchPosts };
}
