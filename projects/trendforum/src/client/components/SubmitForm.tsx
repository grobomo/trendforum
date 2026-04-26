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
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
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
      let imageUrl: string | undefined;
      if (imageFile) {
        const uploaded = await api.upload.image(imageFile);
        imageUrl = uploaded.url;
      }
      const post = await api.posts.create({
        subforumId,
        title: title.trim(),
        body: postType === 'text' ? body.trim() || undefined : undefined,
        linkUrl: postType === 'link' ? linkUrl.trim() || undefined : undefined,
        imageUrl,
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
      <h1 className="text-xl font-bold text-text mb-4">Create a Post</h1>
      <form
        onSubmit={handleSubmit}
        className="bg-card border border-border rounded-md p-4 space-y-4"
      >
        {error && <div className="text-red-400 text-sm">{error}</div>}

        <select
          value={subforumId || ''}
          onChange={(e) => setSubforumId(Number(e.target.value))}
          className="w-full bg-input border border-border rounded p-2 text-text focus:outline-none focus:border-accent transition"
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
              postType === 'text' ? 'bg-border text-white' : 'text-muted'
            }`}
          >
            Text
          </button>
          <button
            type="button"
            onClick={() => setPostType('link')}
            className={`px-3 py-1 rounded text-sm transition ${
              postType === 'link' ? 'bg-border text-white' : 'text-muted'
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
          className="w-full bg-input border border-border rounded p-2 text-text placeholder-dim focus:outline-none focus:border-accent transition"
        />

        {postType === 'text' ? (
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Text (optional)"
            className="w-full bg-input border border-border rounded p-3 text-text placeholder-dim resize-y min-h-[120px] focus:outline-none focus:border-accent transition"
            rows={5}
          />
        ) : (
          <input
            type="url"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            placeholder="URL"
            className="w-full bg-input border border-border rounded p-2 text-text placeholder-dim focus:outline-none focus:border-accent transition"
          />
        )}

        <div>
          <label className="block text-sm text-muted mb-1">Image (optional, max 5MB)</label>
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setImageFile(file);
              if (file) {
                const reader = new FileReader();
                reader.onload = () => setImagePreview(reader.result as string);
                reader.readAsDataURL(file);
              } else {
                setImagePreview(null);
              }
            }}
            className="w-full text-sm text-muted file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-border file:text-text file:cursor-pointer hover:file:bg-[#3a3a5a] transition"
          />
          {imagePreview && (
            <div className="mt-2 relative inline-block">
              <img src={imagePreview} alt="Preview" className="max-h-32 rounded border border-border" />
              <button
                type="button"
                onClick={() => { setImageFile(null); setImagePreview(null); }}
                className="absolute -top-2 -right-2 w-5 h-5 bg-red-600 text-white rounded-full text-xs flex items-center justify-center"
              >
                x
              </button>
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting || !subforumId || !title.trim()}
            className="px-6 py-2 bg-accent text-white rounded font-medium hover:bg-accent-hover disabled:opacity-50 transition"
          >
            {submitting ? 'Posting...' : 'Post'}
          </button>
        </div>
      </form>
    </div>
  );
}
