import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../lib/api';

/**
 * Display grid of approved analytical functions.
 */
export default function FunctionLibrary({ onSelectFunction }) {
  const [functions, setFunctions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFunction, setSelectedFunction] = useState(null);

  useEffect(() => {
    fetchFunctions();
  }, []);

  const fetchFunctions = async () => {
    try {
      const response = await apiFetch('/api/runtime/functions');
      if (!response.ok) throw new Error('Failed to fetch functions');
      const data = await response.json();
      setFunctions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskBadgeColor = (riskLevel) => {
    switch (riskLevel) {
      case 'low':
        return 'bg-green-900/50 text-green-300 border-green-700';
      case 'medium':
        return 'bg-yellow-900/50 text-yellow-300 border-yellow-700';
      case 'high':
        return 'bg-red-900/50 text-red-300 border-red-700';
      default:
        return 'bg-gray-900/50 text-gray-300 border-gray-700';
    }
  };

  const handleFunctionClick = (func) => {
    setSelectedFunction(selectedFunction?.name === func.name ? null : func);
    if (onSelectFunction) {
      onSelectFunction(func);
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
        Error loading functions: {error}
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-400 mb-3">Available Functions</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {functions.map((func) => (
          <div
            key={func.name}
            onClick={() => handleFunctionClick(func)}
            className={`p-4 rounded-lg border cursor-pointer transition-all ${
              selectedFunction?.name === func.name
                ? 'bg-blue-900/30 border-blue-600'
                : 'bg-gray-800 border-gray-700 hover:border-gray-600'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-mono text-sm text-blue-400">{func.name}</h4>
              <span
                className={`text-xs px-2 py-0.5 rounded border ${getRiskBadgeColor(
                  func.risk_level
                )}`}
              >
                {func.risk_level}
              </span>
            </div>
            <p className="text-sm text-gray-300 mb-2">{func.description}</p>
            <div className="text-xs text-gray-500 font-mono truncate">
              {func.signature}
            </div>
            {func.max_runtime && (
              <div className="text-xs text-gray-600 mt-1">
                Max runtime: {func.max_runtime}s
              </div>
            )}

            {/* Expanded details */}
            {selectedFunction?.name === func.name && (
              <div className="mt-3 pt-3 border-t border-gray-700">
                <h5 className="text-xs font-medium text-gray-400 mb-2">Full Signature:</h5>
                <code className="text-xs text-green-400 bg-gray-900 p-2 rounded block overflow-x-auto">
                  {func.signature}
                </code>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
