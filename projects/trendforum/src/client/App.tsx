import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginForm from './components/LoginForm';
import { HomeFeed } from './components/HomeFeed';
import { SubforumFeed } from './components/SubforumFeed';
import { PostDetail } from './components/PostDetail';
import SubmitForm from './components/SubmitForm';
import ModDashboard from './components/ModDashboard';
import { ProfileSetup } from './components/ProfileSetup';
import { ProfilePage } from './components/ProfilePage';
import { PublicProfilePage } from './components/PublicProfilePage';
import { NotificationsPage } from './components/NotificationsPage';
import { useAuth } from './hooks/useAuth';

export default function App() {
  const { token, role, profileId, login, logout } = useAuth();

  if (!token) {
    return <LoginForm onLogin={login} />;
  }

  return (
    <Layout role={role} profileId={profileId} onLogout={logout}>
      <Routes>
        <Route path="/" element={<HomeFeed />} />
        <Route path="/t/:slug" element={<SubforumFeed />} />
        <Route path="/t/:slug/post/:id" element={<PostDetail />} />
        <Route path="/t/:slug/submit" element={<SubmitForm />} />
        <Route path="/login" element={<Navigate to="/" />} />
        <Route path="/mod" element={role === 'admin' ? <ModDashboard /> : <Navigate to="/" />} />
        <Route path="/profile/setup" element={<ProfileSetup />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/u/:username" element={<PublicProfilePage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
      </Routes>
    </Layout>
  );
}
