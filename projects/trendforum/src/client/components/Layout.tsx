import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getSubforums } from '../lib/api';
import SubforumSidebar from './SubforumSidebar';
import { ProfileBadge } from './ProfileBadge';
import { NotificationBell } from './NotificationBell';

interface Props {
  children: React.ReactNode;
  role: string;
  profileId: number | null;
  onLogout: () => void;
}

export default function Layout({ children, role, profileId, onLogout }: Props) {
  const [subforums, setSubforums] = useState<any[]>([]);
  const location = useLocation();

  useEffect(() => {
    getSubforums().then(setSubforums).catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-forum-bg">
      {/* Header */}
      <header className="bg-forum-card border-b border-forum-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-12 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg hover:text-forum-accent transition">
            <span className="text-2xl">🌴</span>
            <span>TrendForum</span>
          </Link>

          <div className="flex items-center gap-4">
            {profileId && <NotificationBell profileId={profileId} />}
            {profileId ? (
              <ProfileBadge profileId={profileId} />
            ) : (
              <Link
                to="/profile/setup"
                className="text-sm text-forum-muted hover:text-forum-accent transition"
              >
                Set Profile
              </Link>
            )}
            {role === 'admin' && (
              <Link
                to="/mod"
                className="text-sm text-forum-muted hover:text-forum-accent transition"
              >
                🛡️ Mod
              </Link>
            )}
            <button
              onClick={onLogout}
              className="text-sm text-forum-muted hover:text-red-400 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="max-w-7xl mx-auto px-4 py-4 flex gap-6">
        {/* Content */}
        <main className="flex-1 min-w-0">
          {children}
        </main>

        {/* Sidebar */}
        <aside className="hidden lg:block w-72 flex-shrink-0">
          <SubforumSidebar
            subforums={subforums}
            currentSlug={location.pathname.match(/^\/t\/([^/]+)/)?.[1]}
          />
        </aside>
      </div>
    </div>
  );
}
