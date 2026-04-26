import { useState } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { SubforumSidebar } from './SubforumSidebar';

export function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length >= 2) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#1a1a2e]">
      <header className="bg-[#16162a] border-b border-[#2a2a4a] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
          <Link to="/" className="text-[#D5232F] font-bold text-xl shrink-0">
            TrendForum
          </Link>
          <form onSubmit={handleSearch} className="mx-4 flex-1 max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts..."
              className="w-full bg-[#1e1e3a] border border-[#2a2a4a] rounded px-3 py-1 text-sm text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
            />
          </form>
          <div className="flex items-center gap-4 shrink-0">
            <Link
              to="/submit"
              className="px-3 py-1 bg-[#D5232F] text-white rounded text-sm hover:bg-red-700 transition"
            >
              New Post
            </Link>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="text-[#8888aa] text-sm hover:text-white transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-4 flex gap-6">
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
        <aside className="w-72 hidden lg:block">
          <SubforumSidebar />
        </aside>
      </div>
    </div>
  );
}
