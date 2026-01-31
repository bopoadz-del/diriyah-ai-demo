import React, { useState, useEffect } from 'react';
import { FileText, Filter, Download, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { apiFetch } from '../../lib/api';

export default function AuditTrail({ userId, startDate, endDate }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    action: 'all',
    decision: 'all',
  });

  useEffect(() => {
    fetchAuditLogs();
  }, [userId, startDate, endDate]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await apiFetch(`/api/pdp/audit-trail?${params}`);
      if (!response.ok) throw new Error('Failed to fetch audit logs');
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Action', 'Resource', 'Decision', 'Reason'],
      ...filteredLogs.map(log => [
        log.timestamp,
        log.action,
        log.resource,
        log.decision,
        log.reason || '',
      ]),
    ]
      .map(row => row.join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-trail-${Date.now()}.csv`;
    a.click();
  };

  const filteredLogs = logs.filter((log) => {
    if (filters.action !== 'all' && log.action !== filters.action) return false;
    if (filters.decision !== 'all' && log.decision !== filters.decision) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-8 w-8 animate-spin text-[#a67c52]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-xl font-semibold text-gray-800">
          <FileText className="h-6 w-6" />
          Audit Trail
        </h2>
        <div className="flex gap-2">
          <button
            onClick={fetchAuditLogs}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 rounded-lg bg-[#a67c52] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <Filter className="h-5 w-5 text-gray-500" />
        <div className="flex flex-1 gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Action:</label>
            <select
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-1 text-sm focus:border-[#a67c52] focus:outline-none"
            >
              <option value="all">All</option>
              <option value="read">Read</option>
              <option value="write">Write</option>
              <option value="delete">Delete</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Decision:</label>
            <select
              value={filters.decision}
              onChange={(e) => setFilters({ ...filters, decision: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-1 text-sm focus:border-[#a67c52] focus:outline-none"
            >
              <option value="all">All</option>
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Decision
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reason
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-sm text-gray-500">
                    No audit logs found
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 capitalize">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.resource}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-1">
                        {log.decision === 'allow' ? (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-600" />
                            <span className="font-medium text-green-700">Allow</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4 text-red-600" />
                            <span className="font-medium text-red-700">Deny</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {log.reason || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
