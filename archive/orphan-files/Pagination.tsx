import { useSearchParams } from 'react-router-dom';

interface PaginationProps {
  hasMore: boolean;
}

export function Pagination({ hasMore }: PaginationProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || '1', 10);

  if (page <= 1 && !hasMore) return null;

  const go = (newPage: number) => {
    const params = new URLSearchParams(searchParams);
    if (newPage <= 1) {
      params.delete('page');
    } else {
      params.set('page', String(newPage));
    }
    setSearchParams(params);
  };

  return (
    <div className="flex items-center justify-center gap-4 mt-4 py-3">
      <button
        onClick={() => go(page - 1)}
        disabled={page <= 1}
        className="px-4 py-1.5 rounded text-sm transition bg-card border border-border text-text hover:border-accent disabled:opacity-30 disabled:hover:border-border"
      >
        Prev
      </button>
      <span className="text-sm text-muted">Page {page}</span>
      <button
        onClick={() => go(page + 1)}
        disabled={!hasMore}
        className="px-4 py-1.5 rounded text-sm transition bg-card border border-border text-text hover:border-accent disabled:opacity-30 disabled:hover:border-border"
      >
        Next
      </button>
    </div>
  );
}
