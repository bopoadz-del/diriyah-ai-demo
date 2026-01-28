import { useCallback, useEffect, useState } from "react";

const fetchJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
};

export const useHydration = (workspaceId) => {
  const [status, setStatus] = useState(null);
  const [runs, setRuns] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadStatus = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson(`/api/hydration/status?workspace_id=${workspaceId}`);
      setStatus(data);
      setRuns(data.recent_runs || []);
      setAlerts(data.alerts || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  const loadSources = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await fetchJson(`/api/hydration/sources?workspace_id=${workspaceId}`);
      setSources(data);
    } catch (err) {
      setError(err.message);
    }
  }, [workspaceId]);

  const runNow = useCallback(
    async (payload = {}) => {
      if (!workspaceId) return;
      return fetchJson("/api/hydration/run-now", {
        method: "POST",
        body: JSON.stringify({ workspace_id: workspaceId, ...payload }),
      });
    },
    [workspaceId],
  );

  useEffect(() => {
    loadStatus();
    loadSources();
  }, [loadStatus, loadSources]);

  return {
    status,
    runs,
    alerts,
    sources,
    loading,
    error,
    reload: async () => {
      await loadStatus();
      await loadSources();
    },
    runNow,
  };
};
