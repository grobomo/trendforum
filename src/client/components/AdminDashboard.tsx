import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { formatTimeAgo } from '../lib/time';

const BASE = '/api';

function getToken() {
  return sessionStorage.getItem('tf_token');
}

async function adminRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

interface Report {
  id: number;
  reason: string;
  createdAt: string;
  post?: { id: number; title: string; subforum: { slug: string } } | null;
  comment?: { id: number; body: string; displayName: string; postId: number } | null;
}

export function AdminDashboard() {
  const { token } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');

  const loadReports = () => {
    setLoading(true);
    adminRequest<Report[]>('/mod/reports')
      .then(setReports)
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  };

  useEffect(loadReports, []);

  const handleAction = async (action: string, targetId: number, targetType: string) => {
    try {
      await adminRequest('/mod/action', {
        method: 'POST',
        body: JSON.stringify({ action, targetId, targetType }),
      });
      setActionMsg(`${action} on ${targetType} #${targetId} — done`);
      loadReports();
    } catch {
      setActionMsg('Action failed');
    }
  };

  if (!token) return <div className="text-[#8888aa] py-8 text-center">Not authenticated.</div>;

  return (
    <div>
      <h1 className="text-xl font-bold text-[#e0e0e0] mb-4">Moderation Queue</h1>

      {actionMsg && (
        <div className="bg-green-900/20 border border-green-800 text-green-400 text-sm rounded p-2 mb-4">
          {actionMsg}
        </div>
      )}

      {loading ? (
        <div className="text-[#8888aa] py-8 text-center">Loading...</div>
      ) : reports.length === 0 ? (
        <div className="text-[#8888aa] py-8 text-center">No reports. All clear!</div>
      ) : (
        <div className="space-y-3">
          {reports.map(report => (
            <div key={report.id} className="bg-[#1e1e3a] border border-[#2a2a4a] rounded-md p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-[#8888aa] mb-1">
                    Report #{report.id} · {formatTimeAgo(report.createdAt)}
                  </div>
                  <div className="text-sm text-[#e0e0e0] mb-2">
                    <span className="text-[#8888aa]">Reason:</span> {report.reason}
                  </div>

                  {report.post && (
                    <div className="bg-[#16162a] rounded p-2 text-sm">
                      <span className="text-[#8888aa]">Post:</span>{' '}
                      <Link
                        to={`/t/${report.post.subforum.slug}/post/${report.post.id}`}
                        className="text-blue-400 hover:underline"
                      >
                        {report.post.title}
                      </Link>
                    </div>
                  )}

                  {report.comment && (
                    <div className="bg-[#16162a] rounded p-2 text-sm">
                      <span className="text-[#8888aa]">Comment by {report.comment.displayName}:</span>{' '}
                      <span className="text-[#e0e0e0]">
                        {report.comment.body.length > 200
                          ? report.comment.body.slice(0, 200) + '...'
                          : report.comment.body}
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-1 shrink-0">
                  {report.post && (
                    <button
                      onClick={() => handleAction('remove_post', report.post!.id, 'post')}
                      className="px-3 py-1 bg-red-800 text-white rounded text-xs hover:bg-red-700 transition"
                    >
                      Remove Post
                    </button>
                  )}
                  {report.comment && (
                    <button
                      onClick={() => handleAction('remove_comment', report.comment!.id, 'comment')}
                      className="px-3 py-1 bg-red-800 text-white rounded text-xs hover:bg-red-700 transition"
                    >
                      Remove Comment
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
