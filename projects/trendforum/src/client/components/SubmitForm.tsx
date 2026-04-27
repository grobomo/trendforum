import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { createPost, getSubforum } from '../lib/api';

export default function SubmitForm() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [subforum, setSubforum] = useState<any>(null);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [postType, setPostType] = useState<'text' | 'link'>('text');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (slug) {
      getSubforum(slug).then(setSubforum).catch(console.error);
    }
  }, [slug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    if (!subforum) {
      setError('Subforum not found');
      return;
    }

    setSubmitting(true);
    try {
      const post = await createPost({
        subforumId: subforum.id,
        title: title.trim(),
        body: postType === 'text' ? body.trim() || undefined : undefined,
        linkUrl: postType === 'link' ? linkUrl.trim() || undefined : undefined,
      });
      navigate(`/t/${slug}/post/${post.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create post');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="text-sm text-forum-muted mb-4">
        <Link to={`/t/${slug}`} className="hover:text-white transition">
          ← t/{slug}
        </Link>
      </div>

      <div className="bg-forum-card border border-forum-border rounded-lg p-6">
        <h1 className="text-xl font-bold text-white mb-4">
          Create a post in t/{slug}
        </h1>

        {/* Post type tabs */}
        <div className="flex gap-0 border border-forum-border rounded-lg overflow-hidden mb-4">
          <button
            onClick={() => setPostType('text')}
            className={`flex-1 px-4 py-2 text-sm font-medium ${
              postType === 'text' ? 'bg-forum-hover text-white' : 'text-forum-muted hover:text-white'
            }`}
          >
            📝 Text
          </button>
          <button
            onClick={() => setPostType('link')}
            className={`flex-1 px-4 py-2 text-sm font-medium border-l border-forum-border ${
              postType === 'link' ? 'bg-forum-hover text-white' : 'text-forum-muted hover:text-white'
            }`}
          >
            🔗 Link
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title"
              maxLength={300}
              className="w-full px-4 py-3 bg-forum-bg border border-forum-border rounded text-white placeholder-forum-muted focus:outline-none focus:border-forum-accent transition"
              autoFocus
            />
            <div className="text-xs text-forum-muted mt-1 text-right">
              {title.length}/300
            </div>
          </div>

          {postType === 'text' ? (
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Text (optional)"
              rows={6}
              className="w-full px-4 py-3 bg-forum-bg border border-forum-border rounded text-white placeholder-forum-muted focus:outline-none focus:border-forum-accent resize-y transition"
            />
          ) : (
            <input
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="https://..."
              className="w-full px-4 py-3 bg-forum-bg border border-forum-border rounded text-white placeholder-forum-muted focus:outline-none focus:border-forum-accent transition"
            />
          )}

          {error && (
            <p className="text-red-400 text-sm mt-2">{error}</p>
          )}

          <div className="flex justify-end mt-4">
            <button
              type="submit"
              disabled={submitting || !title.trim()}
              className="px-6 py-2 bg-forum-accent text-white font-semibold rounded hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {submitting ? 'Posting...' : 'Post'}
            </button>
          </div>
        </form>

        <p className="text-xs text-forum-muted mt-4">
          🔒 Your post is anonymous. No identity is stored or linked.
        </p>
      </div>
    </div>
  );
}
