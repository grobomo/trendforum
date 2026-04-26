import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Layout } from './components/Layout';
import { LoginForm } from './components/LoginForm';
import { HomeFeed } from './components/HomeFeed';
import { SubforumFeed } from './components/SubforumFeed';
import { PostDetail } from './components/PostDetail';
import { SubmitForm } from './components/SubmitForm';
import { SearchResults } from './components/SearchResults';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ProfilePage } from './components/ProfilePage';
import { AdminDashboard } from './components/AdminDashboard';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<HomeFeed />} />
          <Route path="t/:slug" element={<SubforumFeed />} />
          <Route path="t/:slug/post/:id" element={<PostDetail />} />
          <Route path="t/:slug/submit" element={<SubmitForm />} />
          <Route path="submit" element={<SubmitForm />} />
          <Route path="search" element={<SearchResults />} />
          <Route path="u/:pseudonym" element={<ProfilePage />} />
          <Route path="mod" element={<AdminDashboard />} />
        </Route>
      </Routes>
    </AuthProvider>
    </ErrorBoundary>
  );
}
