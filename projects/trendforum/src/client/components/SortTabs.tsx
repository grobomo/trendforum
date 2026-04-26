import { useSearchParams } from 'react-router-dom';

export function SortTabs({ current }: { current: string }) {
  const [, setSearchParams] = useSearchParams();
  const tabs = ['hot', 'new', 'top'];

  return (
    <div className="flex gap-2 mb-4 bg-[#1e1e3a] border border-[#2a2a4a] rounded-md px-3 py-2">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => setSearchParams({ sort: tab })}
          className={`px-3 py-1 rounded text-sm capitalize transition ${
            current === tab
              ? 'bg-[#2a2a4a] text-white font-medium'
              : 'text-[#8888aa] hover:text-white'
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
