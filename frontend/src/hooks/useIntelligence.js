import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

export const useUncertainty = (features) => {
  const [uncertainty, setUncertainty] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const quantify = useCallback(async () => {
    if (!features || (Array.isArray(features) && features.length === 0)) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch('/api/intelligence/predict-with-uncertainty', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features }),
      });
      if (!response.ok) {
        throw new Error('Unable to fetch uncertainty');
      }
      const data = await response.json();
      setUncertainty(data.predictions?.[0] ?? null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [features]);

  useEffect(() => {
    quantify();
  }, [quantify]);

  return { uncertainty, loading, error, refresh: quantify };
};

export const useCausalAnalysis = (projectData, targetVariable = 'schedule_delay') => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyse = useCallback(async () => {
    if (!projectData || projectData.length === 0) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch('/api/intelligence/analyze-delay-causes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_data: projectData, target_variable: targetVariable }),
      });
      if (!response.ok) {
        throw new Error('Unable to analyse project data');
      }
      const data = await response.json();
      setInsights(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [projectData, targetVariable]);

  useEffect(() => {
    analyse();
  }, [analyse]);

  return { insights, loading, error, refresh: analyse };
};

export const useIntelligentAlerts = (projectId) => {
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}/api/intelligence/alerts?project_id=${projectId ?? ''}`;
    const socket = new WebSocket(url);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setAlerts((previous) => [payload, ...previous].slice(0, 100));
      } catch (error) {
        console.warn('Failed to parse alert payload', error);
      }
    };
    return () => socket.close();
  }, [projectId]);

  const acknowledge = useCallback(async (alertId) => {
    await apiFetch(`/api/intelligence/alerts/${alertId}/acknowledge`, { method: 'POST' });
    setAlerts((previous) => previous.map((alert) => (alert.alert_id === alertId ? { ...alert, status: 'acknowledged' } : alert)));
  }, []);

  return { alerts, connected, acknowledge };
};

export default {
  useUncertainty,
  useCausalAnalysis,
  useIntelligentAlerts,
};
