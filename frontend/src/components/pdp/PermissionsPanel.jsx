import React, { useState, useEffect } from 'react';
import { User, Shield, Check, X, RefreshCw } from 'lucide-react';
import { apiFetch } from '../../lib/api';

export default function PermissionsPanel({ projectId }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [permissions, setPermissions] = useState({});

  useEffect(() => {
    fetchUsers();
  }, [projectId]);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/api/pdp/projects/${projectId}/users`);
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserPermissions = async (userId) => {
    try {
      const response = await apiFetch(`/api/pdp/users/${userId}/permissions`);
      if (!response.ok) throw new Error('Failed to fetch permissions');
      const data = await response.json();
      setPermissions(data.permissions || {});
      setSelectedUser(userId);
    } catch (err) {
      console.error('Error fetching permissions:', err);
    }
  };

  const handleGrantAccess = async (userId, resource, action) => {
    try {
      const response = await apiFetch('/api/pdp/access/grant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, resource, action }),
      });
      if (!response.ok) throw new Error('Failed to grant access');
      await fetchUserPermissions(userId);
    } catch (err) {
      console.error('Error granting access:', err);
    }
  };

  const handleRevokeAccess = async (userId, resource, action) => {
    try {
      const response = await apiFetch('/api/pdp/access/revoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, resource, action }),
      });
      if (!response.ok) throw new Error('Failed to revoke access');
      await fetchUserPermissions(userId);
    } catch (err) {
      console.error('Error revoking access:', err);
    }
  };

  const permissionTypes = [
    { resource: 'project', actions: ['read', 'write', 'delete'] },
    { resource: 'document', actions: ['read', 'write', 'delete'] },
    { resource: 'user', actions: ['read', 'write', 'delete'] },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-8 w-8 animate-spin text-[#a67c52]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">Permissions Management</h2>
        <button
          onClick={fetchUsers}
          className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
            <User className="h-5 w-5" />
            Users
          </h3>
          <div className="space-y-2">
            {users.map((user) => (
              <button
                key={user.id}
                onClick={() => fetchUserPermissions(user.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  selectedUser === user.id
                    ? 'border-[#a67c52] bg-[#f6efe6]'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">{user.name}</p>
                    <p className="text-sm text-gray-500">{user.email}</p>
                  </div>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                    {user.role}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 flex items-center gap-2 text-lg font-medium text-gray-800">
            <Shield className="h-5 w-5" />
            Permissions
          </h3>
          {selectedUser ? (
            <div className="space-y-4">
              {permissionTypes.map((perm) => (
                <div key={perm.resource} className="rounded-lg border border-gray-100 p-3">
                  <h4 className="mb-2 font-medium text-gray-700 capitalize">{perm.resource}</h4>
                  <div className="space-y-2">
                    {perm.actions.map((action) => {
                      const hasPermission = permissions[`${perm.resource}:${action}`];
                      return (
                        <div key={action} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600 capitalize">{action}</span>
                          <button
                            onClick={() =>
                              hasPermission
                                ? handleRevokeAccess(selectedUser, perm.resource, action)
                                : handleGrantAccess(selectedUser, perm.resource, action)
                            }
                            className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                              hasPermission
                                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            {hasPermission ? (
                              <>
                                <Check className="h-3 w-3" />
                                Granted
                              </>
                            ) : (
                              <>
                                <X className="h-3 w-3" />
                                Denied
                              </>
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-sm text-gray-500">Select a user to view permissions</p>
          )}
        </div>
      </div>
    </div>
  );
}
