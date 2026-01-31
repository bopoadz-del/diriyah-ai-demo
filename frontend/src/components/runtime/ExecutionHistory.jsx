import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../lib/api';

/**
 * Display list of recent code executions.
 */
export default function ExecutionHistory({ projectId, onSelect }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) {
      setHistory([]);
      setLoading(false);
      return;
    }

    fetchHistory();
  }, [projectId]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiFetch(`/api/runtime/history/${projectId}?limit=20`);
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setHistory(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return (
          <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/30 rounded-lg text-red-300 text-sm">
        Error loading history: {error}
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400">
        <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <p>No execution history yet</p>
        <p className="text-sm mt-1">Run a query to see results here</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-400 mb-3">Recent Executions</h3>
      {history.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelect && onSelect(item)}
          className="w-full text-left p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <div className="flex items-start gap-3">
            {getStatusIcon(item.status)}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-200 truncate">{item.query}</p>
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                <span>{formatDate(item.created_at)}</span>
                {item.execution_time && (
                  <span>{(item.execution_time * 1000).toFixed(0)}ms</span>
                )}
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
