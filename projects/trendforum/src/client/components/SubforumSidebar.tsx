import React from 'react';
import { Link } from 'react-router-dom';

interface Props {
  subforums: any[];
  currentSlug?: string;
}

export default function SubforumSidebar({ subforums, currentSlug }: Props) {
  return (
    <div className="bg-forum-card border border-forum-border rounded-lg overflow-hidden">
      <div className="bg-forum-accent px-4 py-3">
        <h3 className="font-bold text-white text-sm">Subforums</h3>
      </div>

      <div className="p-2">
        <Link
          to="/"
          className={`block px-3 py-2 rounded text-sm transition ${
            !currentSlug
              ? 'bg-forum-hover text-white font-semibold'
              : 'text-forum-muted hover:text-white hover:bg-forum-hover'
          }`}
        >
          🏠 Home (All)
        </Link>

        {subforums.map((sf) => (
          <Link
            key={sf.slug}
            to={`/t/${sf.slug}`}
            className={`block px-3 py-2 rounded text-sm transition ${
              currentSlug === sf.slug
                ? 'bg-forum-hover text-white font-semibold'
                : 'text-forum-muted hover:text-white hover:bg-forum-hover'
            }`}
          >
            <span className="font-medium">t/{sf.slug}</span>
            <span className="text-xs text-forum-muted ml-2">
              {sf._count?.posts || 0}
            </span>
          </Link>
        ))}
      </div>

      <div className="border-t border-forum-border p-3">
        <p className="text-xs text-forum-muted text-center">
          🔒 Anonymous &middot; No tracking
        </p>
      </div>
    </div>
  );
}
