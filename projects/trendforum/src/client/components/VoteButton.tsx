import React, { useState } from 'react';
import { vote } from '../lib/api';

interface Props {
  postId?: number;
  commentId?: number;
  currentScore: number;
}

export default function VoteButton({ postId, commentId, currentScore }: Props) {
  const [score, setScore] = useState(currentScore);
  const [voted, setVoted] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const handleVote = async (value: 1 | -1) => {
    if (loading) return;
    setLoading(true);
    try {
      const result = await vote({ postId, commentId, value });
      setScore(result.score);
      setVoted(result.voted);
    } catch (err) {
      console.error('Vote failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-0.5">
      <button
        onClick={() => handleVote(1)}
        className={`p-1 rounded hover:bg-forum-hover transition text-lg leading-none ${
          voted === 1 ? 'text-forum-upvote' : 'text-forum-muted hover:text-forum-upvote'
        }`}
        title="Upvote"
      >
        ▲
      </button>

      <span className={`text-xs font-bold ${
        score > 0 ? 'text-forum-upvote' : score < 0 ? 'text-forum-downvote' : 'text-forum-muted'
      }`}>
        {score}
      </span>

      <button
        onClick={() => handleVote(-1)}
        className={`p-1 rounded hover:bg-forum-hover transition text-lg leading-none ${
          voted === -1 ? 'text-forum-downvote' : 'text-forum-muted hover:text-forum-downvote'
        }`}
        title="Downvote"
      >
        ▼
      </button>
    </div>
  );
}
