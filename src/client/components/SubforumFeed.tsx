import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { SortTabs } from './SortTabs';
import { Pagination } from './Pagination';

const PER_PAGE = 25;

export function SubforumFeed() {
  const { slug } = useParams<{ slug: string }>();
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';
  const page = parseInt(searchParams.get('page') || '1', 10);

  useEffect(() => {
    if (slug) {
      api.posts.bySubforum(slug, sort, page).then(setPosts).catch(() => {});
    }
  }, [slug, sort, page]);

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
      {posts.length === 0 ? (
        <div className="text-center text-[#8888aa] py-12">No posts in this subforum yet.</div>
      ) : (
        posts.map((post) => <PostCard key={post.id} post={post} />)
      )}
      <Pagination hasMore={posts.length === PER_PAGE} />
    </div>
  );
}
