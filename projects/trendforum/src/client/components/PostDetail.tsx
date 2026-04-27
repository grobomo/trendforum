import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPost, createComment, report } from '../lib/api';
import VoteButton from './VoteButton';
import CommentTree from './CommentTree';

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PostDetail() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const [post, setPost] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [commentBody, setCommentBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState('');

  const fetchPost = async () => {
    try {
      const data = await getPost(parseInt(id!));
      setPost(data);
    } catch (err) {
      console.error('Failed to fetch post:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPost();
  }, [id]);

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentBody.trim()) return;
    setSubmitting(true);
    try {
      await createComment(parseInt(id!), commentBody);
      setCommentBody('');
      fetchPost(); // refresh
    } catch (err) {
      console.error('Failed to create comment:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReport = async () => {
    if (!reportReason.trim()) return;
    try {
      await report({ postId: parseInt(id!), reason: reportReason });
      setShowReport(false);
      setReportReason('');
      alert('Report submitted. Thank you.');
    } catch (err) {
      console.error('Report failed:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-forum-muted">Loading...</div>;
  }

  if (!post) {
    return <div className="text-center py-12 text-red-400">Post not found</div>;
  }

  // Build comment tree
  const rootComments = post.comments?.filter((c: any) => !c.parentId) || [];
  const childMap = new Map<number, any[]>();
  (post.comments || []).forEach((c: any) => {
    if (c.parentId) {
      const children = childMap.get(c.parentId) || [];
      children.push(c);
      childMap.set(c.parentId, children);
    }
  });

  return (
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-forum-muted mb-4">
        <Link to={`/t/${slug}`} className="hover:text-white transition">
          ← t/{slug}
        </Link>
      </div>

      {/* Post */}
      <div className="bg-forum-card border border-forum-border rounded-lg flex">
        <div className="flex flex-col items-center py-4 px-3 bg-forum-bg/50 rounded-l-lg">
          <VoteButton postId={post.id} currentScore={post.score} />
        </div>

        <div className="flex-1 py-4 pr-4">
          <div className="text-xs text-forum-muted mb-1">
            Posted {timeAgo(post.createdAt)}
          </div>

          <h1 className="text-2xl font-bold text-white mb-2">{post.title}</h1>

          {post.body && (
            <div className="text-gray-300 whitespace-pre-wrap mb-3">
              {post.body}
            </div>
          )}

          {post.linkUrl && (
            <a
              href={post.linkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >
              🔗 {post.linkUrl}
            </a>
          )}

          <div className="flex items-center gap-4 mt-4 text-xs text-forum-muted">
            <span>💬 {post._count?.comments || post.comments?.length || 0} comments</span>
            <button
              onClick={() => setShowReport(!showReport)}
              className="hover:text-red-400 transition"
            >
              🚩 Report
            </button>
          </div>

          {showReport && (
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                value={reportReason}
                onChange={(e) => setReportReason(e.target.value)}
                placeholder="Reason for report..."
                className="flex-1 px-3 py-1.5 bg-forum-bg border border-forum-border rounded text-white text-sm focus:outline-none focus:border-forum-accent"
              />
              <button
                onClick={handleReport}
                className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
              >
                Submit
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Comment form */}
      <form onSubmit={handleComment} className="mt-4">
        <textarea
          value={commentBody}
          onChange={(e) => setCommentBody(e.target.value)}
          placeholder="Share your thoughts anonymously..."
          rows={3}
          className="w-full px-4 py-3 bg-forum-card border border-forum-border rounded-lg text-white placeholder-forum-muted focus:outline-none focus:border-forum-accent resize-none transition"
        />
        <div className="flex justify-end mt-2">
          <button
            type="submit"
            disabled={submitting || !commentBody.trim()}
            className="px-4 py-2 bg-forum-accent text-white text-sm font-semibold rounded hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {submitting ? 'Posting...' : 'Comment'}
          </button>
        </div>
      </form>

      {/* Comments tree */}
      <div className="mt-6 space-y-0">
        {rootComments.map((comment: any) => (
          <CommentTree
            key={comment.id}
            comment={comment}
            childMap={childMap}
            postId={parseInt(id!)}
            onRefresh={fetchPost}
            depth={0}
          />
        ))}

        {rootComments.length === 0 && (
          <div className="text-center py-8 text-forum-muted">
            No comments yet. Be the first to chime in.
          </div>
        )}
      </div>
    </div>
  );
}
