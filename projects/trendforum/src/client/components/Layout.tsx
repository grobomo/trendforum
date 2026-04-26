import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { SubforumSidebar } from './SubforumSidebar';

export function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#1a1a2e]">
      <header className="bg-[#16162a] border-b border-[#2a2a4a] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
          <Link to="/" className="text-[#D5232F] font-bold text-xl">
            TrendForum
          </Link>
          <div className="flex items-center gap-4">
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
