import React, { useState } from 'react';
import { createComment, report } from '../lib/api';
import VoteButton from './VoteButton';

interface Props {
  comment: any;
  childMap: Map<number, any[]>;
  postId: number;
  onRefresh: () => void;
  depth: number;
}

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

export default function CommentTree({ comment, childMap, postId, onRefresh, depth }: Props) {
  const [showReply, setShowReply] = useState(false);
  const [replyBody, setReplyBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const children = childMap.get(comment.id) || [];

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyBody.trim()) return;
    setSubmitting(true);
    try {
      await createComment(postId, replyBody, comment.id);
      setReplyBody('');
      setShowReply(false);
      onRefresh();
    } catch (err) {
      console.error('Reply failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReport = async () => {
    const reason = prompt('Reason for report:');
    if (reason) {
      try {
        await report({ commentId: comment.id, reason });
        alert('Report submitted.');
      } catch (err) {
        console.error('Report failed:', err);
      }
    }
  };

  return (
    <div className={`${depth > 0 ? 'ml-6 border-l-2 border-forum-border pl-4' : ''} mt-3`}>
      <div className="flex gap-2">
        {/* Mini vote column for comments */}
        <div className="pt-1">
          <VoteButton commentId={comment.id} currentScore={comment.score} />
        </div>

        <div className="flex-1 min-w-0">
          {/* Comment header */}
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-blue-400">{comment.displayName}</span>
            <span className="text-forum-muted">· {timeAgo(comment.createdAt)}</span>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="text-forum-muted hover:text-white ml-1"
            >
              [{collapsed ? '+' : '−'}]
            </button>
          </div>

          {!collapsed && (
            <>
              {/* Comment body */}
              <div className="text-sm text-gray-300 mt-1 whitespace-pre-wrap">
                {comment.body}
              </div>

              {/* Comment actions */}
              <div className="flex items-center gap-3 mt-1 text-xs text-forum-muted">
                <button
                  onClick={() => setShowReply(!showReply)}
                  className="hover:text-white transition"
                >
                  Reply
                </button>
                <button
                  onClick={handleReport}
                  className="hover:text-red-400 transition"
                >
                  Report
                </button>
              </div>

              {/* Reply form */}
              {showReply && (
                <form onSubmit={handleReply} className="mt-2">
                  <textarea
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    placeholder="Reply..."
                    rows={2}
                    className="w-full px-3 py-2 bg-forum-bg border border-forum-border rounded text-white text-sm placeholder-forum-muted focus:outline-none focus:border-forum-accent resize-none"
                    autoFocus
                  />
                  <div className="flex gap-2 mt-1">
                    <button
                      type="submit"
                      disabled={submitting || !replyBody.trim()}
                      className="px-3 py-1 bg-forum-accent text-white text-xs rounded hover:bg-orange-600 disabled:opacity-50"
                    >
                      {submitting ? '...' : 'Reply'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowReply(false)}
                      className="px-3 py-1 text-xs text-forum-muted hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}

              {/* Children */}
              {children.map((child: any) => (
                <CommentTree
                  key={child.id}
                  comment={child}
                  childMap={childMap}
                  postId={postId}
                  onRefresh={onRefresh}
                  depth={depth + 1}
                />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
