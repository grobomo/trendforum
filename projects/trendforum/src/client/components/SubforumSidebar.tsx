import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api';

export function SubforumSidebar() {
  const [subforums, setSubforums] = useState<any[]>([]);
  const { slug } = useParams();

  useEffect(() => {
    api.subforums.list().then(setSubforums).catch(() => {});
  }, []);

  return (
    <div className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md p-4 sticky top-16">
      <h3 className="text-sm font-bold text-[#e0e0e0] uppercase tracking-wide mb-3">Subforums</h3>
      <div className="space-y-1">
        <Link
          to="/"
          className={`block px-2 py-1.5 rounded text-sm transition ${
            !slug ? 'bg-[#2a2a4a] text-white' : 'text-[#8888aa] hover:text-white hover:bg-[#2a2a4a]/50'
          }`}
        >
          All
        </Link>
        {subforums.map((sf) => (
          <Link
            key={sf.id}
            to={`/t/${sf.slug}`}
            className={`block px-2 py-1.5 rounded text-sm transition ${
              slug === sf.slug
                ? 'bg-[#2a2a4a] text-white'
                : 'text-[#8888aa] hover:text-white hover:bg-[#2a2a4a]/50'
            }`}
          >
            t/{sf.slug}
            <span className="text-xs text-[#666688] ml-1">({sf._count?.posts || 0})</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
