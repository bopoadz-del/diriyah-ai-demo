import React, { useState, useEffect } from 'react';
import { Save, X, AlertCircle } from 'lucide-react';
import { apiFetch } from '../../lib/api';

export default function PolicyForm({ policy, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    name: '',
    type: 'rbac',
    rules: '{}',
    priority: 50,
    enabled: true,
    description: '',
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (policy) {
      setFormData({
        name: policy.name || '',
        type: policy.type || 'rbac',
        rules: typeof policy.rules === 'string' ? policy.rules : JSON.stringify(policy.rules, null, 2),
        priority: policy.priority || 50,
        enabled: policy.enabled !== undefined ? policy.enabled : true,
        description: policy.description || '',
      });
    }
  }, [policy]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Policy name is required';
    }

    if (!formData.type) {
      newErrors.type = 'Policy type is required';
    }

    try {
      JSON.parse(formData.rules);
    } catch (err) {
      newErrors.rules = 'Invalid JSON format';
    }

    if (formData.priority < 0 || formData.priority > 100) {
      newErrors.priority = 'Priority must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...formData,
        rules: JSON.parse(formData.rules),
      };

      const url = policy?.id ? `/api/pdp/policies/${policy.id}` : '/api/pdp/policies';
      const method = policy?.id ? 'PUT' : 'POST';

      const response = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to save policy');
      }

      const data = await response.json();
      if (onSave) {
        onSave(data);
      }
    } catch (err) {
      setErrors({ submit: err.message });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: null });
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">
          {policy?.id ? 'Edit Policy' : 'Create New Policy'}
        </h2>
        {onCancel && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
            title="Cancel"
          >
            <X className="h-6 w-6" />
          </button>
        )}
      </div>

      {errors.submit && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <p className="text-sm text-red-700">{errors.submit}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Policy Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none ${
              errors.name
                ? 'border-red-300 focus:border-red-500'
                : 'border-gray-300 focus:border-[#a67c52]'
            }`}
            placeholder="Enter policy name"
          />
          {errors.name && (
            <p className="mt-1 text-xs text-red-600">{errors.name}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#a67c52] focus:outline-none"
            placeholder="Enter policy description"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Type *
            </label>
            <select
              value={formData.type}
              onChange={(e) => handleChange('type', e.target.value)}
              className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none ${
                errors.type
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-[#a67c52]'
              }`}
            >
              <option value="rbac">RBAC</option>
              <option value="abac">ABAC</option>
              <option value="rate_limit">Rate Limit</option>
              <option value="custom">Custom</option>
            </select>
            {errors.type && (
              <p className="mt-1 text-xs text-red-600">{errors.type}</p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Priority (0-100) *
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={formData.priority}
              onChange={(e) => handleChange('priority', parseInt(e.target.value, 10))}
              className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none ${
                errors.priority
                  ? 'border-red-300 focus:border-red-500'
                  : 'border-gray-300 focus:border-[#a67c52]'
              }`}
            />
            {errors.priority && (
              <p className="mt-1 text-xs text-red-600">{errors.priority}</p>
            )}
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Rules (JSON) *
          </label>
          <textarea
            value={formData.rules}
            onChange={(e) => handleChange('rules', e.target.value)}
            rows={8}
            className={`font-mono w-full rounded-lg border px-3 py-2 text-sm focus:outline-none ${
              errors.rules
                ? 'border-red-300 focus:border-red-500'
                : 'border-gray-300 focus:border-[#a67c52]'
            }`}
            placeholder='{"conditions": [], "effect": "allow"}'
          />
          {errors.rules && (
            <p className="mt-1 text-xs text-red-600">{errors.rules}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Enter policy rules in JSON format
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="enabled"
            checked={formData.enabled}
            onChange={(e) => handleChange('enabled', e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-[#a67c52] focus:ring-[#a67c52]"
          />
          <label htmlFor="enabled" className="text-sm font-medium text-gray-700">
            Enable policy immediately
          </label>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="submit"
            disabled={saving}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#a67c52] px-6 py-3 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : policy?.id ? 'Update Policy' : 'Create Policy'}
          </button>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
