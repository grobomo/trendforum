import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { SortTabs } from './SortTabs';
import { Pagination } from './Pagination';

const PER_PAGE = 25;

export function HomeFeed() {
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';
  const page = parseInt(searchParams.get('page') || '1', 10);

  useEffect(() => {
    api.posts.list(sort, page).then(setPosts).catch(() => {});
  }, [sort, page]);

  return (
    <div>
      <SortTabs current={sort} />
      {posts.length === 0 ? (
        <div className="text-center text-[#8888aa] py-12">No posts yet. Be the first!</div>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
      <Pagination hasMore={posts.length === PER_PAGE} />
    </div>
  );
}
