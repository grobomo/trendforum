import { useState } from 'react';
import { api } from '../lib/api';

interface VoteButtonProps {
  score: number;
  postId?: number;
  commentId?: number;
  compact?: boolean;
}

export function VoteButton({ score, postId, commentId, compact }: VoteButtonProps) {
  const [currentScore, setCurrentScore] = useState(score);
  const [voted, setVoted] = useState<1 | -1 | null>(null);

  const handleVote = async (value: 1 | -1) => {
    try {
      const res = await api.votes.vote({ postId, commentId, value });
      if (res.voted === null) {
        setCurrentScore((prev) => prev - value);
        setVoted(null);
      } else if (voted !== null && voted !== value) {
        setCurrentScore((prev) => prev + value * 2);
        setVoted(value);
      } else {
        setCurrentScore((prev) => prev + value);
        setVoted(value);
      }
    } catch {}
  };

  const upClass = voted === 1 ? 'text-[#D5232F]' : 'text-[#8888aa]';
  const downClass = voted === -1 ? 'text-blue-400' : 'text-[#8888aa]';
  const scoreClass = currentScore > 0 ? 'text-[#D5232F]' : currentScore < 0 ? 'text-blue-400' : 'text-[#8888aa]';

  if (compact) {
    return (
      <span className="inline-flex items-center gap-1 text-xs">
        <button onClick={() => handleVote(1)} className={`${upClass} hover:text-[#D5232F] transition`}>
          +
        </button>
        <span className={`font-bold ${scoreClass}`}>{currentScore}</span>
        <button onClick={() => handleVote(-1)} className={`${downClass} hover:text-blue-400 transition`}>
          -
        </button>
      </span>
    );
  }

  return (
    <div className="flex flex-col items-center w-10 py-2 bg-[#16162a] rounded-l-md shrink-0">
      <button
        onClick={() => handleVote(1)}
        className={`text-lg leading-none ${upClass} hover:text-[#D5232F] transition`}
      >
        &#9650;
      </button>
      <span className={`text-xs font-bold my-1 ${scoreClass}`}>{currentScore}</span>
      <button
        onClick={() => handleVote(-1)}
        className={`text-lg leading-none ${downClass} hover:text-blue-400 transition`}
      >
        &#9660;
      </button>
    </div>
  );
}
