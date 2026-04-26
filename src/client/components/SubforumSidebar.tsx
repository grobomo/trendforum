import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api';

export function SubforumSidebar({ onNavigate }: { onNavigate?: () => void } = {}) {
  const [subforums, setSubforums] = useState<any[]>([]);
  const { slug } = useParams();

  useEffect(() => {
    api.subforums.list().then(setSubforums).catch(() => {});
  }, []);

  return (
    <div className="bg-card border border-border rounded-md p-4 lg:sticky lg:top-16">
      <h3 className="text-sm font-bold text-text uppercase tracking-wide mb-3">Subforums</h3>
      <div className="space-y-1">
        <Link
          to="/"
          onClick={onNavigate}
          className={`block px-2 py-1.5 rounded text-sm transition ${
            !slug ? 'bg-border text-white' : 'text-muted hover:text-text hover:bg-border/50'
          }`}
        >
          All
        </Link>
        {subforums.map((sf) => (
          <Link
            key={sf.id}
            to={`/t/${sf.slug}`}
            onClick={onNavigate}
            className={`block px-2 py-1.5 rounded text-sm transition ${
              slug === sf.slug
                ? 'bg-border text-white'
                : 'text-muted hover:text-text hover:bg-border/50'
            }`}
          >
            t/{sf.slug}
            <span className="text-xs text-dim ml-1">({sf._count?.posts || 0})</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
