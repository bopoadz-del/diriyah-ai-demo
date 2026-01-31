import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

/**
 * Context for managing PDP (Policy Decision Point) state globally.
 * Provides current user permissions, rate limit status, and access control methods.
 */
const PDPContext = createContext(null);

/**
 * Hook to access PDP context.
 * Must be used within a PDPProvider.
 * 
 * @returns {Object} PDP context value
 * @throws {Error} If used outside PDPProvider
 */
export const usePDPContext = () => {
  const context = useContext(PDPContext);
  if (!context) {
    throw new Error('usePDPContext must be used within a PDPProvider');
  }
  return context;
};

/**
 * PDP Provider component that manages global permission and rate limit state.
 * 
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components
 * @param {number} props.userId - Current user ID
 * @param {number} props.projectId - Current project ID (optional)
 * @param {boolean} props.autoRefresh - Enable automatic permission refresh (default: true)
 * @param {number} props.refreshInterval - Auto-refresh interval in ms (default: 300000 = 5 min)
 */
export const PDPProvider = ({ 
  children, 
  userId, 
  projectId = null,
  autoRefresh = true,
  refreshInterval = 300000, // 5 minutes
}) => {
  const [permissions, setPermissions] = useState([]);
  const [rateLimits, setRateLimits] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  /**
   * Fetch and refresh user permissions from the API.
   * 
   * @param {number} targetUserId - User ID to fetch permissions for (defaults to context userId)
   * @param {number} targetProjectId - Project ID to filter permissions (optional)
   * @returns {Promise<Array>} List of permissions
   */
  const refreshPermissions = useCallback(async (targetUserId = null, targetProjectId = null) => {
    const fetchUserId = targetUserId ?? userId;
    if (!fetchUserId) {
      console.warn('No user ID provided for refreshPermissions');
      return [];
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      const projectIdToUse = targetProjectId ?? projectId;
      if (projectIdToUse) {
        params.append('project_id', projectIdToUse);
      }

      const queryString = params.toString();
      const url = `/api/pdp/users/${fetchUserId}/permissions${queryString ? `?${queryString}` : ''}`;
      
      const response = await apiFetch(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch permissions: ${response.status}`);
      }

      const fetchedPermissions = await response.json();
      setPermissions(fetchedPermissions);
      setLastRefresh(new Date());
      return fetchedPermissions;
    } catch (err) {
      setError(err);
      console.error('Error refreshing permissions:', err);
      return [];
    } finally {
      setLoading(false);
    }
  }, [userId, projectId]);

  /**
   * Check if the current user has a specific permission.
   * Checks against cached permissions for fast lookup.
   * 
   * @param {string} permission - Permission string to check (e.g., 'project:read', 'admin:*')
   * @returns {boolean} True if user has the permission
   */
  const hasPermission = useCallback((permission) => {
    if (!permission) return false;
    
    // Check for exact match
    if (permissions.includes(permission)) {
      return true;
    }
    
    // Check for wildcard permissions (e.g., 'admin:*' matches 'admin:read')
    const parts = permission.split(':');
    if (parts.length === 2) {
      const wildcardPerm = `${parts[0]}:*`;
      if (permissions.includes(wildcardPerm)) {
        return true;
      }
    }
    
    // Check for global admin
    if (permissions.includes('*:*') || permissions.includes('admin:*')) {
      return true;
    }
    
    return false;
  }, [permissions]);

  /**
   * Check if user has access to perform an action on a resource.
   * This performs a live check against the PDP API.
   * 
   * @param {string} resource - Resource identifier
   * @param {string} action - Action to check
   * @param {Object} context - Additional context
   * @returns {Promise<Object>} Decision object with 'allowed' and 'reason'
   */
  const checkAccess = useCallback(async (resource, action, context = {}) => {
    if (!userId) {
      return { allowed: false, reason: 'No user ID available' };
    }

    try {
      const response = await apiFetch('/api/pdp/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          action,
          resource,
          context,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Access check failed: ${response.status}`);
      }

      const decision = await response.json();
      return decision;
    } catch (err) {
      console.error('Error checking access:', err);
      return { allowed: false, reason: err.message };
    }
  }, [userId]);

  /**
   * Get rate limit status for a specific endpoint.
   * 
   * @param {string} endpoint - Endpoint identifier
   * @returns {Promise<Object|null>} Rate limit status or null on error
   */
  const getRateLimitStatus = useCallback(async (endpoint) => {
    if (!userId) {
      console.warn('No user ID provided for rate limit check');
      return null;
    }

    try {
      const encodedEndpoint = encodeURIComponent(endpoint);
      const response = await apiFetch(`/api/pdp/rate-limit/${userId}/${encodedEndpoint}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get rate limit: ${response.status}`);
      }

      const status = await response.json();
      
      // Cache the rate limit status
      setRateLimits((prev) => ({
        ...prev,
        [endpoint]: {
          ...status,
          fetchedAt: Date.now(),
        },
      }));

      return status;
    } catch (err) {
      console.error('Error getting rate limit status:', err);
      return null;
    }
  }, [userId]);

  /**
   * Check if a cached rate limit allows more requests.
   * Returns true if no cached data (optimistic).
   * 
   * @param {string} endpoint - Endpoint identifier
   * @returns {boolean} True if rate limit allows requests
   */
  const isRateLimitOk = useCallback((endpoint) => {
    const cached = rateLimits[endpoint];
    if (!cached) return true; // Optimistic: allow if no data
    
    // Check if cached data is stale (older than 60 seconds)
    const age = Date.now() - cached.fetchedAt;
    if (age > 60000) return true; // Stale, allow
    
    return cached.remaining > 0;
  }, [rateLimits]);

  // Initial permissions fetch
  useEffect(() => {
    if (userId) {
      refreshPermissions();
    }
  }, [userId, projectId, refreshPermissions]);

  // Auto-refresh permissions
  useEffect(() => {
    if (!autoRefresh || !userId) return;

    const intervalId = setInterval(() => {
      refreshPermissions();
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, userId, refreshPermissions]);

  const value = {
    // State
    permissions,
    rateLimits,
    loading,
    error,
    lastRefresh,
    userId,
    projectId,

    // Methods
    refreshPermissions,
    hasPermission,
    checkAccess,
    getRateLimitStatus,
    isRateLimitOk,
  };

  return (
    <PDPContext.Provider value={value}>
      {children}
    </PDPContext.Provider>
  );
};

export default PDPContext;
