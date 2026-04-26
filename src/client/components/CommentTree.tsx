import { useState } from 'react';
import { Link } from 'react-router-dom';
import { VoteButton } from './VoteButton';
import { api } from '../lib/api';
import { formatTimeAgo } from '../lib/time';
import { Markdown } from './Markdown';

interface Comment {
  id: number;
  postId: number;
  parentId: number | null;
  displayName: string;
  body: string;
  score: number;
  createdAt: string;
}

function buildTree(comments: Comment[]): Map<number | null, Comment[]> {
  const tree = new Map<number | null, Comment[]>();
  for (const c of comments) {
    const key = c.parentId;
    if (!tree.has(key)) tree.set(key, []);
    tree.get(key)!.push(c);
  }
  return tree;
}

function CommentNode({
  comment,
  tree,
  postId,
  onReply,
  depth,
}: {
  comment: Comment;
  tree: Map<number | null, Comment[]>;
  postId: number;
  onReply: () => void;
  depth: number;
}) {
  const [replying, setReplying] = useState(false);
  const [replyBody, setReplyBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const children = tree.get(comment.id) || [];

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyBody.trim()) return;
    setSubmitting(true);
    try {
      await api.comments.create(postId, { body: replyBody, parentId: comment.id });
      setReplyBody('');
      setReplying(false);
      onReply();
    } finally {
      setSubmitting(false);
    }
  };

  const isCoconut = comment.displayName === 'Coconut';

  return (
    <div className={`${depth > 0 ? 'ml-6 border-l-2 border-border pl-4' : ''} mt-3`}>
      <div className="flex items-center gap-2 text-xs">
        {!isCoconut && !comment.displayName.startsWith('Anon-') ? (
          <Link to={`/u/${comment.displayName}`} className="font-medium text-accent hover:underline">
            {comment.displayName}
          </Link>
        ) : (
          <span className={`font-medium ${isCoconut ? 'text-yellow-400' : 'text-accent'}`}>
            {isCoconut ? 'Coconut' : comment.displayName}
          </span>
        )}
        <span className="text-dim">&middot;</span>
        <span className="text-dim">{formatTimeAgo(comment.createdAt)}</span>
      </div>
      <Markdown content={comment.body} className="text-text text-sm mt-1" />
      <div className="flex items-center gap-3 mt-1">
        <VoteButton score={comment.score} commentId={comment.id} compact />
        <button
          onClick={() => setReplying(!replying)}
          className="text-xs text-muted hover:text-text transition"
        >
          Reply
        </button>
      </div>

      {replying && (
        <form onSubmit={handleReply} className="mt-2">
          <textarea
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Write a reply..."
            className="w-full bg-input border border-border rounded p-2 text-sm text-text placeholder-dim resize-y focus:outline-none focus:border-accent transition"
            rows={2}
          />
          <div className="flex gap-2 mt-1">
            <button
              type="submit"
              disabled={submitting || !replyBody.trim()}
              className="px-3 py-1 bg-accent text-white rounded text-xs hover:bg-accent-hover disabled:opacity-50 transition"
            >
              Reply
            </button>
            <button
              type="button"
              onClick={() => setReplying(false)}
              className="px-3 py-1 text-muted text-xs hover:text-text transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {children.map((child) => (
        <CommentNode
          key={child.id}
          comment={child}
          tree={tree}
          postId={postId}
          onReply={onReply}
          depth={depth + 1}
        />
      ))}
    </div>
  );
}

export function CommentTree({
  comments,
  postId,
  onReply,
}: {
  comments: Comment[];
  postId: number;
  onReply: () => void;
}) {
  const tree = buildTree(comments);
  const roots = tree.get(null) || [];

  if (roots.length === 0) {
    return <div className="text-muted text-sm py-4">No comments yet.</div>;
  }

  return (
    <div>
      {roots.map((comment) => (
        <CommentNode
          key={comment.id}
          comment={comment}
          tree={tree}
          postId={postId}
          onReply={onReply}
          depth={0}
        />
      ))}
    </div>
  );
}
