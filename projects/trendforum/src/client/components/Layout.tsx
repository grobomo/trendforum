import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { SubforumSidebar } from './SubforumSidebar';

export function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length >= 2) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchOpen(false);
    }
  };

  // Close drawer on navigation
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-[#1a1a2e]">
      <header className="bg-[#16162a] border-b border-[#2a2a4a] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-2 sm:px-4 h-12 flex items-center justify-between gap-2">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setDrawerOpen(!drawerOpen)}
            className="lg:hidden text-[#8888aa] hover:text-white p-1 shrink-0"
            aria-label="Menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {drawerOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>

          <Link to="/" className="text-[#D5232F] font-bold text-lg sm:text-xl shrink-0">
            TrendForum
          </Link>

          {/* Search — full on md+, icon toggle on mobile */}
          <form onSubmit={handleSearch} className="hidden sm:flex mx-4 flex-1 max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts..."
              className="w-full bg-[#1e1e3a] border border-[#2a2a4a] rounded px-3 py-1 text-sm text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
            />
          </form>
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="sm:hidden text-[#8888aa] hover:text-white p-1 shrink-0"
            aria-label="Search"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>

          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <Link
              to="/submit"
              className="px-2 sm:px-3 py-1 bg-[#D5232F] text-white rounded text-xs sm:text-sm hover:bg-red-700 transition"
            >
              <span className="hidden sm:inline">New Post</span>
              <span className="sm:hidden">+</span>
            </Link>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="text-[#8888aa] text-xs sm:text-sm hover:text-white transition"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Mobile search bar — slides down */}
        {searchOpen && (
          <form onSubmit={handleSearch} className="sm:hidden px-2 pb-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts..."
              autoFocus
              className="w-full bg-[#1e1e3a] border border-[#2a2a4a] rounded px-3 py-1.5 text-sm text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
            />
          </form>
        )}
      </header>

      {/* Drawer overlay — mobile only */}
      {drawerOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex" onClick={() => setDrawerOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="relative w-64 max-w-[80vw] bg-[#16162a] border-r border-[#2a2a4a] p-4 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <SubforumSidebar onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-2 sm:px-4 py-3 sm:py-4 flex gap-6">
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
