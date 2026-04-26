import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { SortTabs } from './SortTabs';

export function HomeFeed() {
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';

  useEffect(() => {
    api.posts.list(sort).then(setPosts).catch(() => {});
  }, [sort]);

  return (
    <div>
      <SortTabs current={sort} />
      {posts.length === 0 ? (
        <div className="text-center text-[#8888aa] py-12">No posts yet. Be the first!</div>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
    </div>
  );
}
