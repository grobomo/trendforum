import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function ProfileMenu() {
  const { profile, loginProfile, registerProfile, dropProfile } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [pseudonym, setPseudonym] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (profile) {
    return (
      <div className="flex items-center gap-2">
        <Link
          to={`/u/${profile.pseudonym}`}
          className="text-accent text-xs sm:text-sm font-medium hover:text-red-400 transition"
        >
          {profile.pseudonym}
        </Link>
        <button
          onClick={() => dropProfile()}
          className="text-dim text-xs hover:text-muted transition"
          title="Go anonymous"
        >
          Drop ID
        </button>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') {
        await registerProfile(pseudonym, password);
      } else {
        await loginProfile(pseudonym, password);
      }
      setShowModal(false);
      setPseudonym('');
      setPassword('');
    } catch (err: any) {
      setError(err.message || 'Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="text-muted text-xs sm:text-sm hover:text-text transition"
      >
        Claim ID
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setShowModal(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="relative bg-card border border-border rounded-lg p-6 w-full max-w-sm"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold text-text mb-1">
              {mode === 'register' ? 'Claim a Pseudonym' : 'Sign In'}
            </h2>
            <p className="text-muted text-xs mb-4">
              {mode === 'register'
                ? 'Pick a name that persists across sessions.'
                : 'Log in with your existing pseudonym.'}
            </p>

            {error && (
              <div className="bg-red-900/20 border border-red-800 text-red-400 text-sm rounded p-2 mb-3">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                type="text"
                value={pseudonym}
                onChange={e => setPseudonym(e.target.value)}
                placeholder="Pseudonym"
                autoFocus
                className="w-full bg-input border border-border rounded p-2 text-sm text-text placeholder-dim focus:outline-none focus:border-accent transition"
              />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Password (6+ chars)"
                className="w-full bg-input border border-border rounded p-2 text-sm text-text placeholder-dim focus:outline-none focus:border-accent transition"
              />
              <button
                type="submit"
                disabled={loading || !pseudonym || !password}
                className="w-full py-2 bg-accent text-white rounded text-sm font-medium hover:bg-accent-hover disabled:opacity-50 transition"
              >
                {loading ? 'Working...' : mode === 'register' ? 'Claim' : 'Sign In'}
              </button>
            </form>

            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
              className="text-muted text-xs mt-3 hover:text-text transition block text-center w-full"
            >
              {mode === 'login' ? 'Need a pseudonym? Register' : 'Already have one? Sign in'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
