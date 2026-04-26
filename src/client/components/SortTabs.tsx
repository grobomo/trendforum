import { useSearchParams } from 'react-router-dom';

export function SortTabs({ current }: { current: string }) {
  const [, setSearchParams] = useSearchParams();
  const tabs = ['hot', 'new', 'top'];

  return (
    <div className="flex gap-2 mb-4 bg-card border border-border rounded-md px-3 py-2">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => setSearchParams({ sort: tab })}
          className={`px-3 py-1 rounded text-sm capitalize transition ${
            current === tab
              ? 'bg-border text-white font-medium'
              : 'text-muted hover:text-text'
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
