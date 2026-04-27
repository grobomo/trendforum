import { useState } from 'react';

interface Props {
  onLogin: (password: string, admin?: boolean) => Promise<void>;
}

export default function LoginForm({ onLogin }: Props) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await onLogin(password, isAdmin);
    } catch (err: any) {
      setError(err.message || 'Invalid password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-forum-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🌴</div>
          <h1 className="text-3xl font-bold text-white">TrendForum</h1>
          <p className="text-forum-muted mt-2">Anonymous. Candid. Yours.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-forum-card border border-forum-border rounded-lg p-6">
          <label className="block text-sm text-forum-muted mb-2">
            {isAdmin ? 'Enter admin password' : 'Enter the WiFi password to prove you\'re a Trender'}
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isAdmin ? 'Admin password...' : 'WiFi password...'}
            className="w-full px-3 py-2 bg-forum-bg border border-forum-border rounded text-white placeholder-forum-muted focus:outline-none focus:border-forum-accent transition"
            autoFocus
          />

          {error && (
            <p className="text-red-400 text-sm mt-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full mt-4 px-4 py-2 bg-forum-accent text-white font-semibold rounded hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Verifying...' : 'Enter'}
          </button>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => { setIsAdmin(!isAdmin); setError(''); }}
              className="text-xs text-forum-muted hover:text-forum-accent transition"
            >
              {isAdmin ? 'Back to Trender login' : 'Admin login'}
            </button>
          </div>

          <p className="text-xs text-forum-muted mt-3 text-center">
            No accounts. No tracking. Just a password.
          </p>
        </form>
      </div>
    </div>
  );
}
