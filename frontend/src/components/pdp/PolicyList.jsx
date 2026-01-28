import React, { useState, useEffect } from 'react';
import { Shield, Plus, RefreshCw, Search, ToggleLeft, ToggleRight } from 'lucide-react';

export default function PolicyList({ onEdit, onCreate }) {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/pdp/policies');
      if (!response.ok) throw new Error('Failed to fetch policies');
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (policy) => {
    try {
      const response = await fetch(`/api/pdp/policies/${policy.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...policy, enabled: !policy.enabled }),
      });
      if (!response.ok) throw new Error('Failed to update policy');
      await fetchPolicies();
    } catch (err) {
      console.error('Error toggling policy:', err);
    }
  };

  const filteredPolicies = policies.filter((policy) =>
    policy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    policy.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPriorityColor = (priority) => {
    if (priority >= 90) return 'bg-red-100 text-red-700';
    if (priority >= 70) return 'bg-orange-100 text-orange-700';
    if (priority >= 50) return 'bg-yellow-100 text-yellow-700';
    return 'bg-blue-100 text-blue-700';
  };

  const getTypeColor = (type) => {
    const colors = {
      rbac: 'bg-purple-100 text-purple-700',
      abac: 'bg-indigo-100 text-indigo-700',
      rate_limit: 'bg-green-100 text-green-700',
      custom: 'bg-gray-100 text-gray-700',
    };
    return colors[type] || 'bg-gray-100 text-gray-700';
  };

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
          <Shield className="h-6 w-6" />
          Active Policies
        </h2>
        <div className="flex gap-2">
          <button
            onClick={fetchPolicies}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          {onCreate && (
            <button
              onClick={onCreate}
              className="flex items-center gap-2 rounded-lg bg-[#a67c52] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              <Plus className="h-4 w-4" />
              New Policy
            </button>
          )}
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search policies..."
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-[#a67c52] focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredPolicies.length === 0 ? (
          <div className="col-span-full rounded-lg border border-gray-200 bg-white p-8 text-center">
            <Shield className="mx-auto mb-2 h-12 w-12 text-gray-300" />
            <p className="text-sm text-gray-500">No policies found</p>
          </div>
        ) : (
          filteredPolicies.map((policy) => (
            <div
              key={policy.id}
              className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="mb-3 flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-800">{policy.name}</h3>
                  <p className="mt-1 text-xs text-gray-500">{policy.description || 'No description'}</p>
                </div>
                <button
                  onClick={() => handleToggleEnabled(policy)}
                  className="text-gray-400 hover:text-gray-600"
                  title={policy.enabled ? 'Disable policy' : 'Enable policy'}
                >
                  {policy.enabled ? (
                    <ToggleRight className="h-6 w-6 text-green-600" />
                  ) : (
                    <ToggleLeft className="h-6 w-6 text-gray-400" />
                  )}
                </button>
              </div>

              <div className="mb-3 flex flex-wrap gap-2">
                <span className={`rounded-full px-2 py-1 text-xs font-medium uppercase ${getTypeColor(policy.type)}`}>
                  {policy.type}
                </span>
                <span className={`rounded-full px-2 py-1 text-xs font-medium ${getPriorityColor(policy.priority)}`}>
                  Priority: {policy.priority}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${policy.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />
                  <span className="text-xs text-gray-600">
                    {policy.enabled ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {onEdit && (
                  <button
                    onClick={() => onEdit(policy)}
                    className="text-xs font-medium text-[#a67c52] hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
