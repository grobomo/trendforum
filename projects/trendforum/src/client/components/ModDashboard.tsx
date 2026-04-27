import React, { useState, useEffect } from 'react';
import { getReports, modAction } from '../lib/api';

export default function ModDashboard() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      const data = await getReports();
      setReports(data);
    } catch (err) {
      console.error('Failed to fetch reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleAction = async (report: any, action: string) => {
    const targetType = report.postId ? 'post' : 'comment';
    const targetId = report.postId || report.commentId;

    try {
      await modAction({
        action,
        targetId,
        targetType,
        reason: report.reason,
      });
      // Remove from list
      setReports((prev) => prev.filter((r) => r.id !== report.id));
    } catch (err) {
      console.error('Mod action failed:', err);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-forum-muted">Loading reports...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">🛡️ Moderation Dashboard</h1>

      {reports.length === 0 && (
        <div className="text-center py-12">
          <p className="text-forum-muted text-lg">No reports. All clear! 🌴</p>
        </div>
      )}

      <div className="space-y-3">
        {reports.map((report) => (
          <div
            key={report.id}
            className="bg-forum-card border border-forum-border rounded-lg p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-xs text-forum-muted mb-1">
                  {report.postId ? `Post #${report.postId}` : `Comment #${report.commentId}`}
                  {report.post && `: "${report.post.title}"`}
                  {report.comment && `: "${report.comment.body?.slice(0, 80)}..." by ${report.comment.displayName}`}
                </div>
                <div className="text-sm text-red-400">
                  🚩 {report.reason}
                </div>
                <div className="text-xs text-forum-muted mt-1">
                  {new Date(report.createdAt).toLocaleString()}
                </div>
              </div>

              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => handleAction(report, report.postId ? 'remove_post' : 'remove_comment')}
                  className="px-3 py-1.5 bg-red-600 text-white text-xs rounded hover:bg-red-700 transition"
                >
                  Remove
                </button>
                <button
                  onClick={() => setReports((prev) => prev.filter((r) => r.id !== report.id))}
                  className="px-3 py-1.5 bg-forum-hover text-forum-muted text-xs rounded hover:text-white transition"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
