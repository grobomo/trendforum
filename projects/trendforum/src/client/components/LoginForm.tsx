import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function LoginForm() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, token } = useAuth();
  const navigate = useNavigate();

  if (token) {
    navigate('/', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(password);
      navigate('/', { replace: true });
    } catch (e: any) {
      setError(e.message || 'Invalid password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#1a1a2e] flex items-center justify-center">
      <div className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-lg p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-[#D5232F] text-center mb-2">TrendForum</h1>
        <p className="text-[#8888aa] text-center text-sm mb-6">
          Enter this month's BYOD WiFi password to continue
        </p>

        {error && (
          <div className="bg-red-900/20 border border-red-800 text-red-400 text-sm rounded p-2 mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="WiFi password"
            autoFocus
            className="w-full bg-[#16162a] border border-[#2a2a4a] rounded p-3 text-[#e0e0e0] placeholder-[#666688] focus:outline-none focus:border-[#D5232F] transition mb-4"
          />
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-3 bg-[#D5232F] text-white rounded font-medium hover:bg-red-700 disabled:opacity-50 transition"
          >
            {loading ? 'Verifying...' : 'Enter'}
          </button>
        </form>

        <p className="text-[#666688] text-xs text-center mt-4">
          Anonymous. No accounts. No tracking.
        </p>
      </div>
    </div>
  );
}
