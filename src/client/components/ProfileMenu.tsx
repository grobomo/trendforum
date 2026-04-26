import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function ProfileMenu() {
  const { profile, loginProfile, registerProfile } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [pseudonym, setPseudonym] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (profile) {
    return (
      <Link
        to={`/u/${profile.pseudonym}`}
        className="text-[#D5232F] text-xs sm:text-sm font-medium hover:text-red-400 transition"
      >
        {profile.pseudonym}
      </Link>
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
        className="text-[#8888aa] text-xs sm:text-sm hover:text-white transition"
      >
        Claim ID
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setShowModal(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="relative bg-[#1e1e3a] border border-[#2a2a4a] rounded-lg p-6 w-full max-w-sm"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold text-[#e0e0e0] mb-1">
              {mode === 'register' ? 'Claim a Pseudonym' : 'Sign In'}
            </h2>
            <p className="text-[#8888aa] text-xs mb-4">
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
                className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-sm text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
              />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Password (6+ chars)"
                className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-2 text-sm text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition"
              />
              <button
                type="submit"
                disabled={loading || !pseudonym || !password}
                className="w-full py-2 bg-[#D5232F] text-white rounded text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition"
              >
                {loading ? 'Working...' : mode === 'register' ? 'Claim' : 'Sign In'}
              </button>
            </form>

            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
              className="text-[#8888aa] text-xs mt-3 hover:text-white transition block text-center w-full"
            >
              {mode === 'login' ? 'Need a pseudonym? Register' : 'Already have one? Sign in'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
