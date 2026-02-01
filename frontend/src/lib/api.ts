const API_BASE = import.meta.env.VITE_API_URL || '';
const DEFAULT_WORKSPACE = import.meta.env.VITE_WORKSPACE_ID || 'demo';
const DEFAULT_USER = import.meta.env.VITE_USER_ID || 'demo';
const DEFAULT_TENANT = 'demo';

const safeGet = (k: string) => {
  try {
    return localStorage.getItem(k);
  } catch {
    return null;
  }
};

export const getWorkspaceId = () => safeGet('workspace_id') || DEFAULT_WORKSPACE;
export const getUserId = () => safeGet('user_id') || DEFAULT_USER;
export const getTenantId = () => safeGet('tenant_id') || DEFAULT_TENANT;

export const apiFetch = (path: string, options: RequestInit = {}) => {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const headers = new Headers(options.headers || {});

  // Set tenant/workspace/user headers
  if (!headers.has('X-Tenant-ID')) {
    headers.set('X-Tenant-ID', getTenantId());
  }
  if (!headers.has('X-Workspace-ID')) {
    headers.set('X-Workspace-ID', getWorkspaceId());
  }
  if (!headers.has('X-User-ID')) {
    headers.set('X-User-ID', getUserId());
  }

  // Only set Content-Type: application/json when body exists and is not FormData
  if (options.body && !(options.body instanceof FormData)) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
  }

  return fetch(url, { ...options, headers, credentials: 'include' });
};
