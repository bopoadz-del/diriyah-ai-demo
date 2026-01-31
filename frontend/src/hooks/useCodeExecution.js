import { useState, useCallback } from 'react';
import { apiFetch } from '../lib/api';

/**
 * React hook for code execution API.
 *
 * @returns {Object} - { execute, generateOnly, loading, result, error, generatedCode }
 */
export function useCodeExecution() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [generatedCode, setGeneratedCode] = useState('');

  /**
   * Execute a query (generate and run code).
   *
   * @param {string} query - Natural language query
   * @param {Object} context - Additional context (project_id, etc.)
   * @param {boolean} dryRun - If true, only generate code without executing
   */
  const execute = useCallback(async (query, context = {}, dryRun = false) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiFetch('/api/runtime/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          project_id: context.project_id || null,
          context: context.context || null,
          dry_run: dryRun,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setGeneratedCode(data.generated_code || '');
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Generate code only (without executing).
   *
   * @param {string} query - Natural language query
   * @param {Object} context - Additional context
   */
  const generateOnly = useCallback(async (query, context = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiFetch('/api/runtime/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          project_id: context.project_id || null,
          context: context.context || null,
          dry_run: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setGeneratedCode(data.generated_code || '');
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Validate code without executing.
   *
   * @param {string} code - Python code to validate
   */
  const validate = useCallback(async (code) => {
    try {
      const response = await apiFetch('/api/runtime/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(code),
      });

      if (!response.ok) {
        throw new Error('Validation request failed');
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  /**
   * Get execution history for a project.
   *
   * @param {number} projectId - Project ID
   * @param {number} limit - Max records to fetch
   */
  const getHistory = useCallback(async (projectId, limit = 50) => {
    try {
      const response = await apiFetch(
        `/api/runtime/history/${projectId}?limit=${limit}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  /**
   * Get list of approved functions.
   */
  const getFunctions = useCallback(async () => {
    try {
      const response = await apiFetch('/api/runtime/functions');

      if (!response.ok) {
        throw new Error('Failed to fetch functions');
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  /**
   * Clear current results and errors.
   */
  const clear = useCallback(() => {
    setResult(null);
    setError(null);
    setGeneratedCode('');
  }, []);

  return {
    execute,
    generateOnly,
    validate,
    getHistory,
    getFunctions,
    clear,
    loading,
    result,
    error,
    generatedCode,
  };
}

export default useCodeExecution;
