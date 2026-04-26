import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { SubforumSidebar } from './SubforumSidebar';
import { ErrorBoundary } from './ErrorBoundary';
import { ProfileMenu } from './ProfileMenu';
import { useTheme } from '../hooks/useTheme';

export function Layout() {
  const { logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
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
    <div className="min-h-screen bg-page">
      <header className="bg-input border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-2 sm:px-4 h-12 flex items-center justify-between gap-2">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setDrawerOpen(!drawerOpen)}
            className="lg:hidden text-muted hover:text-text p-1 shrink-0"
            aria-label="Menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {drawerOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>

          <Link to="/" className="text-accent font-bold text-lg sm:text-xl shrink-0">
            TrendForum
          </Link>

          {/* Search — full on md+, icon toggle on mobile */}
          <form onSubmit={handleSearch} className="hidden sm:flex mx-4 flex-1 max-w-md">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search posts..."
              className="w-full bg-card border border-border rounded px-3 py-1 text-sm text-text placeholder-dim focus:outline-none focus:border-accent transition"
            />
          </form>
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="sm:hidden text-muted hover:text-text p-1 shrink-0"
            aria-label="Search"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>

          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <button
              onClick={toggleTheme}
              className="text-muted hover:text-text p-1 transition"
              aria-label="Toggle theme"
              title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
            >
              {theme === 'dark' ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>
            <ProfileMenu />
            <Link
              to="/submit"
              className="px-2 sm:px-3 py-1 bg-accent text-white rounded text-xs sm:text-sm hover:bg-accent-hover transition"
            >
              <span className="hidden sm:inline">New Post</span>
              <span className="sm:hidden">+</span>
            </Link>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="text-muted text-xs sm:text-sm hover:text-text transition"
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
              className="w-full bg-card border border-border rounded px-3 py-1.5 text-sm text-text placeholder-dim focus:outline-none focus:border-accent transition"
            />
          </form>
        )}
      </header>

      {/* Drawer overlay — mobile only */}
      {drawerOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex" onClick={() => setDrawerOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="relative w-64 max-w-[80vw] bg-input border-r border-border p-4 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <SubforumSidebar onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-2 sm:px-4 py-3 sm:py-4 flex gap-6">
        <main className="flex-1 min-w-0">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
        <aside className="w-72 hidden lg:block">
          <SubforumSidebar />
        </aside>
      </div>
    </div>
  );
}
