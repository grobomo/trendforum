import React from 'react';

interface Props {
  sort: string;
  onSort: (sort: string) => void;
}

const tabs = [
  { key: 'hot', label: '🔥 Hot' },
  { key: 'new', label: '🆕 New' },
  { key: 'top', label: '⬆️ Top' },
];

export default function SortTabs({ sort, onSort }: Props) {
  return (
    <div className="bg-forum-card border border-forum-border rounded-lg flex overflow-hidden">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onSort(tab.key)}
          className={`px-4 py-2 text-sm font-medium transition ${
            sort === tab.key
              ? 'bg-forum-hover text-white'
              : 'text-forum-muted hover:bg-forum-hover hover:text-white'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
