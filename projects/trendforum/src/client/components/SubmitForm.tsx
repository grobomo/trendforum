import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api';

export function SubmitForm() {
  const navigate = useNavigate();
  const { slug } = useParams();
  const [subforums, setSubforums] = useState<any[]>([]);
  const [subforumId, setSubforumId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [postType, setPostType] = useState<'text' | 'link'>('text');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.subforums.list().then((sfs) => {
      setSubforums(sfs);
      if (slug) {
        const match = sfs.find((sf: any) => sf.slug === slug);
        if (match) setSubforumId(match.id);
      }
    });
  }, [slug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subforumId || !title.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const post = await api.posts.create({
        subforumId,
        title: title.trim(),
        body: postType === 'text' ? body.trim() || undefined : undefined,
        linkUrl: postType === 'link' ? linkUrl.trim() || undefined : undefined,
      });
      const sf = subforums.find((s) => s.id === subforumId);
      navigate(`/t/${sf?.slug || 'general'}/post/${post.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-bold text-[#e0e0e0] mb-4">Create a Post</h1>
      <form
        onSubmit={handleSubmit}
        className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md p-4 space-y-4"
      >
        {error && <div className="text-red-400 text-sm">{error}</div>}

        <select
          value={subforumId || ''}
          onChange={(e) => setSubforumId(Number(e.target.value))}
          className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-[#e0e0e0] focus:outline-none focus:border-[#D5232F] transition"
        >
          <option value="">Choose a subforum</option>
          {subforums.map((sf) => (
            <option key={sf.id} value={sf.id}>
              t/{sf.slug}
            </option>
          ))}
        </select>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPostType('text')}
            className={`px-3 py-1 rounded text-sm transition ${
              postType === 'text' ? 'bg-[#2a2a4a] text-white' : 'text-[#8888aa]'
            }`}
          >
            Text
          </button>
          <button
            type="button"
            onClick={() => setPostType('link')}
            className={`px-3 py-1 rounded text-sm transition ${
              postType === 'link' ? 'bg-[#2a2a4a] text-white' : 'text-[#8888aa]'
            }`}
          >
            Link
          </button>
        </div>

        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          maxLength={300}
          className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
        />

        {postType === 'text' ? (
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Text (optional)"
            className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-3 text-[#e0e0e0] placeholder-[#666688] resize-y min-h-[120px] focus:outline-none focus:border-[#D5232F] transition"
            rows={5}
          />
        ) : (
          <input
            type="url"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            placeholder="URL"
            className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
          />
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting || !subforumId || !title.trim()}
            className="px-6 py-2 bg-[#D5232F] text-white rounded font-medium hover:bg-red-700 disabled:opacity-50 transition"
          >
            {submitting ? 'Posting...' : 'Post'}
          </button>
        </div>
      </form>
    </div>
  );
}
