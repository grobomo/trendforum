import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';
import { SortTabs } from './SortTabs';

export function SubforumFeed() {
  const { slug } = useParams<{ slug: string }>();
  const [posts, setPosts] = useState<any[]>([]);
  const [searchParams] = useSearchParams();
  const sort = searchParams.get('sort') || 'hot';

  useEffect(() => {
    if (slug) {
      api.posts.bySubforum(slug, sort).then(setPosts).catch(() => {});
    }
  }, [slug, sort]);

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
    </div>
  );
}
