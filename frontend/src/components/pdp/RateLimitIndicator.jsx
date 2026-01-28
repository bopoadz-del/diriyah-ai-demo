import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react';

export default function RateLimitIndicator({ userId, endpoint }) {
  const [rateLimit, setRateLimit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRateLimit();
    const interval = setInterval(fetchRateLimit, 30000);
    return () => clearInterval(interval);
  }, [userId, endpoint]);

  const fetchRateLimit = async () => {
    if (!userId || !endpoint) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`/api/pdp/rate-limit/${userId}/${endpoint}`);
      if (!response.ok) throw new Error('Failed to fetch rate limit');
      const data = await response.json();
      setRateLimit(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!userId || !endpoint) {
    return null;
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-center">
          <RefreshCw className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-2 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  if (!rateLimit) {
    return null;
  }

  const { remaining, limit, reset_at } = rateLimit;
  const percentage = (remaining / limit) * 100;
  const isLow = percentage < 20;
  const isCritical = percentage < 10;

  const getProgressColor = () => {
    if (isCritical) return 'bg-red-600';
    if (isLow) return 'bg-yellow-600';
    return 'bg-green-600';
  };

  const getBackgroundColor = () => {
    if (isCritical) return 'bg-red-100';
    if (isLow) return 'bg-yellow-100';
    return 'bg-green-100';
  };

  const resetTime = reset_at ? new Date(reset_at).toLocaleTimeString() : 'Unknown';

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-gray-600" />
          <h3 className="font-medium text-gray-800">Rate Limit</h3>
        </div>
        <button
          onClick={fetchRateLimit}
          className="text-gray-400 hover:text-gray-600"
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Remaining requests:</span>
          <span className={`font-semibold ${isCritical ? 'text-red-700' : isLow ? 'text-yellow-700' : 'text-green-700'}`}>
            {remaining} / {limit}
          </span>
        </div>

        <div className="relative h-3 overflow-hidden rounded-full bg-gray-200">
          <div
            className={`h-full transition-all duration-500 ${getProgressColor()}`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Endpoint: {endpoint}</span>
          <span>Resets at {resetTime}</span>
        </div>

        {isCritical && (
          <div className={`flex items-center gap-2 rounded-lg p-2 text-xs ${getBackgroundColor()}`}>
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <span className="text-red-800">Rate limit almost exceeded!</span>
          </div>
        )}
      </div>
    </div>
  );
}
