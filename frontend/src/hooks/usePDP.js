import { useCallback, useState } from 'react';

/**
 * React hook for PDP (Policy Decision Point) operations.
 * Provides methods for permission checking, access management, rate limiting, and audit trails.
 * 
 * @returns {Object} PDP operations and state
 * @returns {Function} checkPermission - Check if user has permission for resource/action
 * @returns {Function} grantAccess - Grant user access to a project
 * @returns {Function} revokeAccess - Revoke user access from a project
 * @returns {Function} getRateLimit - Get rate limit status for an endpoint
 * @returns {Function} getAuditTrail - Get filtered audit trail logs
 * @returns {boolean} loading - Loading state for operations
 * @returns {Error|null} error - Last error encountered
 */
export const usePDP = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Check if a user has permission to perform an action on a resource.
   * 
   * @param {string} resource - Resource identifier (e.g., 'project:123')
   * @param {string} action - Action to check (e.g., 'read', 'write', 'delete')
   * @param {number} userId - User ID to check permissions for
   * @param {Object} context - Additional context for policy evaluation
   * @returns {Promise<Object>} Decision object with 'allowed' boolean and 'reason'
   */
  const checkPermission = useCallback(async (resource, action, userId, context = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/pdp/evaluate', {
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
        throw new Error(errorData.detail || `Permission check failed: ${response.status}`);
      }

      const decision = await response.json();
      return decision;
    } catch (err) {
      setError(err);
      console.error('Error checking permission:', err);
      return { allowed: false, reason: err.message };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Grant user access to a project with specified role.
   * 
   * @param {number} userId - User ID to grant access
   * @param {number} projectId - Project ID
   * @param {string} role - Role to assign ('viewer', 'contributor', 'admin', 'owner')
   * @param {number} grantedBy - User ID who is granting access
   * @param {Date|string} expiresAt - Optional expiration date
   * @returns {Promise<Object>} ACL entry with granted permissions
   */
  const grantAccess = useCallback(async (userId, projectId, role, grantedBy = null, expiresAt = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        user_id: userId,
        project_id: projectId,
        role,
      });
      
      if (grantedBy !== null) {
        params.append('granted_by', grantedBy);
      }
      
      if (expiresAt !== null) {
        const expiryDate = expiresAt instanceof Date ? expiresAt.toISOString() : expiresAt;
        params.append('expires_at', expiryDate);
      }

      const response = await fetch(`/api/pdp/access/grant?${params.toString()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to grant access: ${response.status}`);
      }

      const entry = await response.json();
      return entry;
    } catch (err) {
      setError(err);
      console.error('Error granting access:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Revoke user access from a project.
   * 
   * @param {number} userId - User ID to revoke access
   * @param {number} projectId - Project ID
   * @returns {Promise<Object>} Success message
   */
  const revokeAccess = useCallback(async (userId, projectId) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        user_id: userId,
        project_id: projectId,
      });

      const response = await fetch(`/api/pdp/access/revoke?${params.toString()}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to revoke access: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (err) {
      setError(err);
      console.error('Error revoking access:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Get rate limit status for a user and endpoint.
   * 
   * @param {number} userId - User ID
   * @param {string} endpoint - Endpoint identifier (e.g., '/chat', '/query')
   * @returns {Promise<Object>} Rate limit status with limit, remaining, reset_time
   */
  const getRateLimit = useCallback(async (userId, endpoint) => {
    setLoading(true);
    setError(null);
    
    try {
      const encodedEndpoint = encodeURIComponent(endpoint);
      const response = await fetch(`/api/pdp/rate-limit/${userId}/${encodedEndpoint}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get rate limit: ${response.status}`);
      }

      const status = await response.json();
      return status;
    } catch (err) {
      setError(err);
      console.error('Error getting rate limit:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Get audit trail with optional filters.
   * 
   * @param {Object} filters - Filter options
   * @param {number} filters.userId - Filter by user ID
   * @param {string} filters.action - Filter by action
   * @param {string} filters.resourceType - Filter by resource type
   * @param {Date|string} filters.startDate - Filter by start date
   * @param {Date|string} filters.endDate - Filter by end date
   * @param {number} filters.limit - Maximum records to return (default: 100, max: 1000)
   * @returns {Promise<Array>} List of audit log entries
   */
  const getAuditTrail = useCallback(async (filters = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      
      if (filters.userId) params.append('user_id', filters.userId);
      if (filters.action) params.append('action', filters.action);
      if (filters.resourceType) params.append('resource_type', filters.resourceType);
      if (filters.startDate) {
        const startDate = filters.startDate instanceof Date 
          ? filters.startDate.toISOString() 
          : filters.startDate;
        params.append('start_date', startDate);
      }
      if (filters.endDate) {
        const endDate = filters.endDate instanceof Date 
          ? filters.endDate.toISOString() 
          : filters.endDate;
        params.append('end_date', endDate);
      }
      if (filters.limit) params.append('limit', filters.limit);

      const queryString = params.toString();
      const url = `/api/pdp/audit-trail${queryString ? `?${queryString}` : ''}`;
      
      const response = await fetch(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get audit trail: ${response.status}`);
      }

      const logs = await response.json();
      return logs;
    } catch (err) {
      setError(err);
      console.error('Error getting audit trail:', err);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    checkPermission,
    grantAccess,
    revokeAccess,
    getRateLimit,
    getAuditTrail,
    loading,
    error,
  };
};

export default usePDP;
