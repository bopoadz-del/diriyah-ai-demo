import { useCallback, useState } from 'react';

interface PDPDecision {
  allowed: boolean;
  reason: string;
}

interface RateLimitStatus {
  limit: number;
  remaining: number;
  reset_time?: string;
}

interface AuditLogEntry {
  [key: string]: unknown;
}

interface GrantAccessParams {
  userId: number;
  projectId: number;
  role: string;
  grantedBy?: number | null;
  expiresAt?: Date | string | null;
}

interface AuditFilters {
  userId?: number;
  action?: string;
  resourceType?: string;
  startDate?: Date | string;
  endDate?: Date | string;
  limit?: number;
}

export const usePDP = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const checkPermission = useCallback(
    async (
      resource: string,
      action: string,
      userId: number,
      context: Record<string, unknown> = {},
    ): Promise<PDPDecision> => {
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

        const decision = (await response.json()) as PDPDecision;
        return decision;
      } catch (err) {
        const resolvedError = err instanceof Error ? err : new Error('Unknown error');
        setError(resolvedError);
        console.error('Error checking permission:', resolvedError);
        return { allowed: false, reason: resolvedError.message };
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const grantAccess = useCallback(
    async ({ userId, projectId, role, grantedBy = null, expiresAt = null }: GrantAccessParams) => {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          user_id: String(userId),
          project_id: String(projectId),
          role,
        });

        if (grantedBy !== null) {
          params.append('granted_by', String(grantedBy));
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

        return response.json();
      } catch (err) {
        const resolvedError = err instanceof Error ? err : new Error('Unknown error');
        setError(resolvedError);
        console.error('Error granting access:', resolvedError);
        throw resolvedError;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const revokeAccess = useCallback(async (userId: number, projectId: number) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        user_id: String(userId),
        project_id: String(projectId),
      });

      const response = await fetch(`/api/pdp/access/revoke?${params.toString()}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to revoke access: ${response.status}`);
      }

      return response.json();
    } catch (err) {
      const resolvedError = err instanceof Error ? err : new Error('Unknown error');
      setError(resolvedError);
      console.error('Error revoking access:', resolvedError);
      throw resolvedError;
    } finally {
      setLoading(false);
    }
  }, []);

  const getRateLimit = useCallback(async (userId: number, endpoint: string): Promise<RateLimitStatus | null> => {
    setLoading(true);
    setError(null);

    try {
      const encodedEndpoint = encodeURIComponent(endpoint);
      const response = await fetch(`/api/pdp/rate-limit/${userId}/${encodedEndpoint}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get rate limit: ${response.status}`);
      }

      return (await response.json()) as RateLimitStatus;
    } catch (err) {
      const resolvedError = err instanceof Error ? err : new Error('Unknown error');
      setError(resolvedError);
      console.error('Error getting rate limit:', resolvedError);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getAuditTrail = useCallback(async (filters: AuditFilters = {}): Promise<AuditLogEntry[]> => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();

      if (filters.userId) params.append('user_id', String(filters.userId));
      if (filters.action) params.append('action', filters.action);
      if (filters.resourceType) params.append('resource_type', filters.resourceType);
      if (filters.startDate) {
        const startDate = filters.startDate instanceof Date ? filters.startDate.toISOString() : filters.startDate;
        params.append('start_date', startDate);
      }
      if (filters.endDate) {
        const endDate = filters.endDate instanceof Date ? filters.endDate.toISOString() : filters.endDate;
        params.append('end_date', endDate);
      }
      if (filters.limit) params.append('limit', String(filters.limit));

      const queryString = params.toString();
      const url = `/api/pdp/audit-trail${queryString ? `?${queryString}` : ''}`;

      const response = await fetch(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get audit trail: ${response.status}`);
      }

      return (await response.json()) as AuditLogEntry[];
    } catch (err) {
      const resolvedError = err instanceof Error ? err : new Error('Unknown error');
      setError(resolvedError);
      console.error('Error getting audit trail:', resolvedError);
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
