import { useState, useCallback, useEffect } from 'react';

/**
 * Hook for fetching document links from the ULE API.
 * Follows the existing hook pattern from useIntelligence.js
 */
export const useDocumentLinks = (documentId, options = {}) => {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { confidenceThreshold = 0.75, maxLinks = 100 } = options;

  const fetchLinks = useCallback(async () => {
    if (!documentId) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        confidence_threshold: confidenceThreshold,
        max_links: maxLinks,
      });

      const response = await fetch(
        `/api/reasoning/links/${documentId}?${params}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch document links');
      }

      const data = await response.json();
      setLinks(data.links || []);
    } catch (err) {
      setError(err);
      setLinks([]);
    } finally {
      setLoading(false);
    }
  }, [documentId, confidenceThreshold, maxLinks]);

  useEffect(() => {
    fetchLinks();
  }, [fetchLinks]);

  return { links, loading, error, refresh: fetchLinks };
};

/**
 * Hook for finding links for a text query.
 */
export const useFindLinks = () => {
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const findLinks = useCallback(async (text, options = {}) => {
    if (!text) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/reasoning/link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          project_id: options.projectId,
          document_type: options.documentType || 'general',
          confidence_threshold: options.confidenceThreshold || 0.75,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to find links');
      }

      const data = await response.json();
      setLinks(data.links || []);
      return data;
    } catch (err) {
      setError(err);
      setLinks([]);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { links, loading, error, findLinks };
};

/**
 * Hook for fetching the knowledge graph for a project.
 */
export const useKnowledgeGraph = (projectId) => {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchGraph = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/reasoning/graph/${projectId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch knowledge graph');
      }

      const data = await response.json();
      setGraph({
        nodes: data.nodes || [],
        edges: data.edges || [],
        stats: data.stats || {},
      });
    } catch (err) {
      setError(err);
      setGraph({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return { graph, loading, error, refresh: fetchGraph };
};

/**
 * Hook for fetching link evidence.
 */
export const useLinkEvidence = (linkId) => {
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchEvidence = useCallback(async () => {
    if (!linkId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/reasoning/evidence/${linkId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch link evidence');
      }

      const data = await response.json();
      setEvidence(data);
    } catch (err) {
      setError(err);
      setEvidence(null);
    } finally {
      setLoading(false);
    }
  }, [linkId]);

  useEffect(() => {
    fetchEvidence();
  }, [fetchEvidence]);

  return { evidence, loading, error, refresh: fetchEvidence };
};

export default useDocumentLinks;
