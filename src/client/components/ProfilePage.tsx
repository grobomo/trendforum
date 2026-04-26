import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { PostCard } from './PostCard';

export function ProfilePage() {
  const { pseudonym } = useParams();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!pseudonym) return;
    setLoading(true);
    api.profile.get(pseudonym)
      .then(res => setProfile(res.profile))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [pseudonym]);

  if (loading) return <div className="text-[#8888aa] py-8 text-center">Loading...</div>;
  if (!profile) return <div className="text-[#8888aa] py-8 text-center">Profile not found.</div>;

  return (
    <div>
      <div className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md p-4 mb-4">
        <h1 className="text-xl font-bold text-[#e0e0e0]">{profile.pseudonym}</h1>
        <div className="text-sm text-[#8888aa] mt-1">
          Joined {new Date(profile.createdAt).toLocaleDateString()}
          {' · '}
          {profile._count.posts} posts
          {' · '}
          {profile._count.comments} comments
        </div>
      </div>

      <h2 className="text-sm font-bold text-[#8888aa] uppercase tracking-wide mb-3">Recent Posts</h2>
      {profile.posts.length === 0 ? (
        <div className="text-[#8888aa] text-sm py-4">No posts yet.</div>
      ) : (
        profile.posts.map((post: any) => <PostCard key={post.id} post={post} />)
      )}
    </div>
  );
}
