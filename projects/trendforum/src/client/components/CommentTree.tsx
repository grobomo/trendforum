import { useState } from 'react';
import { VoteButton } from './VoteButton';
import { api } from '../lib/api';
import { formatTimeAgo } from '../lib/time';

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
    <div className={`${depth > 0 ? 'ml-6 border-l-2 border-[#2a2a4a] pl-4' : ''} mt-3`}>
      <div className="flex items-center gap-2 text-xs">
        <span className={`font-medium ${isCoconut ? 'text-yellow-400' : 'text-[#D5232F]'}`}>
          {isCoconut ? 'Coconut' : comment.displayName}
        </span>
        <span className="text-[#666688]">&middot;</span>
        <span className="text-[#666688]">{formatTimeAgo(comment.createdAt)}</span>
      </div>
      <p className="text-[#e0e0e0] text-sm mt-1 whitespace-pre-wrap">{comment.body}</p>
      <div className="flex items-center gap-3 mt-1">
        <VoteButton score={comment.score} commentId={comment.id} compact />
        <button
          onClick={() => setReplying(!replying)}
          className="text-xs text-[#8888aa] hover:text-white transition"
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
            className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-sm text-[#e0e0e0] placeholder-[#666688] resize-y focus:outline-none focus:border-[#D5232F] transition"
            rows={2}
          />
          <div className="flex gap-2 mt-1">
            <button
              type="submit"
              disabled={submitting || !replyBody.trim()}
              className="px-3 py-1 bg-[#D5232F] text-white rounded text-xs hover:bg-red-700 disabled:opacity-50 transition"
            >
              Reply
            </button>
            <button
              type="button"
              onClick={() => setReplying(false)}
              className="px-3 py-1 text-[#8888aa] text-xs hover:text-white transition"
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
    return <div className="text-[#8888aa] text-sm py-4">No comments yet.</div>;
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
