import React, { useState, useEffect } from 'react';

const AdminPanel = ({ user, onClose }) => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState({});
  const [projects, setProjects] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);

  // Form states
  const [newUser, setNewUser] = useState({
    username: '',
    email: '',
    role: '',
    projects: [],
    active: true
  });

  const [newRole, setNewRole] = useState({
    name: '',
    description: '',
    permissions: {
      allowed_documents: [],
      data_access: [],
      permissions: []
    }
  });

  const [editingUser, setEditingUser] = useState(null);
  const [editingRole, setEditingRole] = useState(null);

  useEffect(() => {
    if (activeTab === 'dashboard') {
      loadDashboard();
    } else if (activeTab === 'users') {
      loadUsers();
    } else if (activeTab === 'roles') {
      loadRoles();
    } else if (activeTab === 'projects') {
      loadProjects();
    }
  }, [activeTab]);

  const apiCall = async (endpoint, options = {}) => {
    const token = localStorage.getItem('auth_token');
    const response = await fetch(`/api/admin${endpoint}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'API call failed');
    }
    
    return response.json();
  };

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/dashboard');
      setStats(data.stats);
      setUsers(Object.entries(data.data.users).map(([username, userData]) => ({
        username,
        ...userData
      })));
      setRoles(data.data.roles);
      setProjects(data.data.projects);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    }
    setLoading(false);
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/users');
      setUsers(Object.entries(data.users).map(([username, userData]) => ({
        username,
        ...userData
      })));
    } catch (error) {
      console.error('Failed to load users:', error);
    }
    setLoading(false);
  };

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/roles');
      setRoles(data.roles);
    } catch (error) {
      console.error('Failed to load roles:', error);
    }
    setLoading(false);
  };

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await apiCall('/projects');
      setProjects(data.projects);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
    setLoading(false);
  };

  const createUser = async () => {
    try {
      await apiCall('/users', {
        method: 'POST',
        body: JSON.stringify(newUser)
      });
      
      setNewUser({
        username: '',
        email: '',
        role: '',
        projects: [],
        active: true
      });
      
      loadUsers();
      alert('User created successfully!');
    } catch (error) {
      alert(`Failed to create user: ${error.message}`);
    }
  };

  const updateUser = async (username, updates) => {
    try {
      await apiCall(`/users/${username}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      
      loadUsers();
      setEditingUser(null);
      alert('User updated successfully!');
    } catch (error) {
      alert(`Failed to update user: ${error.message}`);
    }
  };

  const deleteUser = async (username) => {
    if (!confirm(`Are you sure you want to delete user ${username}?`)) {
      return;
    }
    
    try {
      await apiCall(`/users/${username}`, {
        method: 'DELETE'
      });
      
      loadUsers();
      alert('User deleted successfully!');
    } catch (error) {
      alert(`Failed to delete user: ${error.message}`);
    }
  };

  const createRole = async () => {
    try {
      await apiCall('/roles', {
        method: 'POST',
        body: JSON.stringify(newRole)
      });
      
      setNewRole({
        name: '',
        description: '',
        permissions: {
          allowed_documents: [],
          data_access: [],
          permissions: []
        }
      });
      
      loadRoles();
      alert('Role created successfully!');
    } catch (error) {
      alert(`Failed to create role: ${error.message}`);
    }
  };

  const updateRole = async (roleName, updates) => {
    try {
      await apiCall(`/roles/${roleName}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      
      loadRoles();
      setEditingRole(null);
      alert('Role updated successfully!');
    } catch (error) {
      alert(`Failed to update role: ${error.message}`);
    }
  };

  const bulkUpdateUsers = async (updates) => {
    if (selectedUsers.length === 0) {
      alert('Please select users to update');
      return;
    }
    
    try {
      await apiCall('/bulk-update', {
        method: 'POST',
        body: JSON.stringify({
          users: selectedUsers,
          updates
        })
      });
      
      setSelectedUsers([]);
      loadUsers();
      alert(`Successfully updated ${selectedUsers.length} users!`);
    } catch (error) {
      alert(`Failed to bulk update users: ${error.message}`);
    }
  };

  const documentTypes = [
    'boq', 'schedules', 'contracts', 'rfis', 'ncrs', 'moms', 
    'technical_drawings', 'financials', 'quotes'
  ];

  const dataAccessTypes = [
    'all', 'operational', 'technical', 'commercial', 'financial'
  ];

  const permissionTypes = [
    'read', 'write', 'edit', 'delete', 'admin'
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-800">Admin Panel</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 bg-gray-50 border-r">
            <nav className="p-4 space-y-2">
              {[
                { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
                { id: 'users', label: '👥 Users', icon: '👥' },
                { id: 'roles', label: '🔐 Roles', icon: '🔐' },
                { id: 'projects', label: '📁 Projects', icon: '📁' },
                { id: 'activity', label: '📋 Activity Log', icon: '📋' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-amber-100 text-amber-800 border border-amber-200'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-auto p-6">
            {loading && (
              <div className="flex items-center justify-center h-64">
                <div className="text-lg text-gray-600">Loading...</div>
              </div>
            )}

            {/* Dashboard Tab */}
            {activeTab === 'dashboard' && !loading && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold">Dashboard Overview</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <div className="text-2xl font-bold text-blue-600">{stats.total_users || 0}</div>
                    <div className="text-blue-800">Total Users</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <div className="text-2xl font-bold text-green-600">{stats.total_roles || 0}</div>
                    <div className="text-green-800">Total Roles</div>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                    <div className="text-2xl font-bold text-purple-600">{stats.total_projects || 0}</div>
                    <div className="text-purple-800">Total Projects</div>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                    <div className="text-2xl font-bold text-orange-600">{stats.recent_activities?.length || 0}</div>
                    <div className="text-orange-800">Recent Activities</div>
                  </div>
                </div>

                {/* Users by Role Chart */}
                <div className="bg-white p-4 rounded-lg border">
                  <h4 className="font-semibold mb-4">Users by Role</h4>
                  <div className="space-y-2">
                    {Object.entries(stats.users_by_role || {}).map(([role, count]) => (
                      <div key={role} className="flex items-center justify-between">
                        <span className="capitalize">{role}</span>
                        <span className="bg-gray-100 px-2 py-1 rounded text-sm">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Activities */}
                <div className="bg-white p-4 rounded-lg border">
                  <h4 className="font-semibold mb-4">Recent Activities</h4>
                  <div className="space-y-2 max-h-64 overflow-auto">
                    {stats.recent_activities?.map((activity, index) => (
                      <div key={index} className="flex items-center justify-between text-sm border-b pb-2">
                        <div>
                          <span className="font-medium">{activity.user_id}</span>
                          <span className="text-gray-600 ml-2">{activity.action}</span>
                        </div>
                        <span className="text-gray-500">
                          {new Date(activity.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Users Tab */}
            {activeTab === 'users' && !loading && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-semibold">User Management</h3>
                  <div className="flex space-x-2">
                    {selectedUsers.length > 0 && (
                      <div className="flex space-x-2">
                        <select
                          onChange={(e) => {
                            if (e.target.value) {
                              bulkUpdateUsers({ role: e.target.value });
                              e.target.value = '';
                            }
                          }}
                          className="px-3 py-1 border rounded text-sm"
                        >
                          <option value="">Bulk Change Role</option>
                          {Object.keys(roles).map(role => (
                            <option key={role} value={role}>{role}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => bulkUpdateUsers({ active: false })}
                          className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
                        >
                          Deactivate Selected
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Create User Form */}
                <div className="bg-gray-50 p-4 rounded-lg border">
                  <h4 className="font-semibold mb-4">Create New User</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <input
                      type="text"
                      placeholder="Username"
                      value={newUser.username}
                      onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                      className="px-3 py-2 border rounded"
                    />
                    <input
                      type="email"
                      placeholder="Email"
                      value={newUser.email}
                      onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                      className="px-3 py-2 border rounded"
                    />
                    <select
                      value={newUser.role}
                      onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                      className="px-3 py-2 border rounded"
                    >
                      <option value="">Select Role</option>
                      {Object.keys(roles).map(role => (
                        <option key={role} value={role}>{role}</option>
                      ))}
                    </select>
                    <button
                      onClick={createUser}
                      disabled={!newUser.username || !newUser.email || !newUser.role}
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
                    >
                      Create User
                    </button>
                  </div>
                </div>

                {/* Users Table */}
                <div className="bg-white rounded-lg border overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          <input
                            type="checkbox"
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedUsers(users.map(u => u.username));
                              } else {
                                setSelectedUsers([]);
                              }
                            }}
                          />
                        </th>
                        <th className="px-4 py-3 text-left">Username</th>
                        <th className="px-4 py-3 text-left">Email</th>
                        <th className="px-4 py-3 text-left">Role</th>
                        <th className="px-4 py-3 text-left">Projects</th>
                        <th className="px-4 py-3 text-left">Status</th>
                        <th className="px-4 py-3 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(user => (
                        <tr key={user.username} className="border-t">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedUsers.includes(user.username)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedUsers([...selectedUsers, user.username]);
                                } else {
                                  setSelectedUsers(selectedUsers.filter(u => u !== user.username));
                                }
                              }}
                            />
                          </td>
                          <td className="px-4 py-3 font-medium">{user.username}</td>
                          <td className="px-4 py-3">{user.email}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                              {user.role}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {user.projects?.slice(0, 2).map(project => (
                                <span key={project} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                  {project}
                                </span>
                              ))}
                              {user.projects?.length > 2 && (
                                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                                  +{user.projects.length - 2}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-sm ${
                              user.active 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {user.active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex space-x-2">
                              <button
                                onClick={() => setEditingUser(user)}
                                className="text-blue-600 hover:text-blue-800 text-sm"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => deleteUser(user.username)}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Roles Tab */}
            {activeTab === 'roles' && !loading && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold">Role Management</h3>

                {/* Create Role Form */}
                <div className="bg-gray-50 p-4 rounded-lg border">
                  <h4 className="font-semibold mb-4">Create New Role</h4>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <input
                        type="text"
                        placeholder="Role Name"
                        value={newRole.name}
                        onChange={(e) => setNewRole({...newRole, name: e.target.value})}
                        className="px-3 py-2 border rounded"
                      />
                      <input
                        type="text"
                        placeholder="Description"
                        value={newRole.description}
                        onChange={(e) => setNewRole({...newRole, description: e.target.value})}
                        className="px-3 py-2 border rounded"
                      />
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Allowed Documents</label>
                        <div className="space-y-1 max-h-32 overflow-auto border rounded p-2">
                          {documentTypes.map(doc => (
                            <label key={doc} className="flex items-center">
                              <input
                                type="checkbox"
                                checked={newRole.permissions.allowed_documents.includes(doc)}
                                onChange={(e) => {
                                  const docs = newRole.permissions.allowed_documents;
                                  if (e.target.checked) {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        allowed_documents: [...docs, doc]
                                      }
                                    });
                                  } else {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        allowed_documents: docs.filter(d => d !== doc)
                                      }
                                    });
                                  }
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm">{doc}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium mb-2">Data Access</label>
                        <div className="space-y-1 max-h-32 overflow-auto border rounded p-2">
                          {dataAccessTypes.map(access => (
                            <label key={access} className="flex items-center">
                              <input
                                type="checkbox"
                                checked={newRole.permissions.data_access.includes(access)}
                                onChange={(e) => {
                                  const accesses = newRole.permissions.data_access;
                                  if (e.target.checked) {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        data_access: [...accesses, access]
                                      }
                                    });
                                  } else {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        data_access: accesses.filter(a => a !== access)
                                      }
                                    });
                                  }
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm">{access}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium mb-2">Permissions</label>
                        <div className="space-y-1 max-h-32 overflow-auto border rounded p-2">
                          {permissionTypes.map(perm => (
                            <label key={perm} className="flex items-center">
                              <input
                                type="checkbox"
                                checked={newRole.permissions.permissions.includes(perm)}
                                onChange={(e) => {
                                  const perms = newRole.permissions.permissions;
                                  if (e.target.checked) {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        permissions: [...perms, perm]
                                      }
                                    });
                                  } else {
                                    setNewRole({
                                      ...newRole,
                                      permissions: {
                                        ...newRole.permissions,
                                        permissions: perms.filter(p => p !== perm)
                                      }
                                    });
                                  }
                                }}
                                className="mr-2"
                              />
                              <span className="text-sm">{perm}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    <button
                      onClick={createRole}
                      disabled={!newRole.name}
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
                    >
                      Create Role
                    </button>
                  </div>
                </div>

                {/* Roles List */}
                <div className="space-y-4">
                  {Object.entries(roles).map(([roleName, roleData]) => (
                    <div key={roleName} className="bg-white p-4 rounded-lg border">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-lg">{roleName}</h4>
                        <button
                          onClick={() => setEditingRole({ name: roleName, ...roleData })}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          Edit
                        </button>
                      </div>
                      <p className="text-gray-600 mb-3">{roleData.description}</p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <strong>Documents:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {roleData.allowed_documents?.map(doc => (
                              <span key={doc} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                                {doc}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <strong>Data Access:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {roleData.data_access?.map(access => (
                              <span key={access} className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                                {access}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <strong>Permissions:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {roleData.permissions?.map(perm => (
                              <span key={perm} className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                                {perm}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Projects Tab */}
            {activeTab === 'projects' && !loading && (
              <div className="space-y-6">
                <h3 className="text-xl font-semibold">Project Management</h3>
                
                <div className="bg-white p-4 rounded-lg border">
                  <h4 className="font-semibold mb-4">Projects</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map(project => (
                      <div key={project} className="p-3 border rounded-lg">
                        <div className="font-medium">{project.replace('_', ' ').toUpperCase()}</div>
                        <div className="text-sm text-gray-600 mt-1">
                          Users: {users.filter(u => u.projects?.includes(project)).length}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Edit User: {editingUser.username}</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={editingUser.email}
                  onChange={(e) => setEditingUser({...editingUser, email: e.target.value})}
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <select
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({...editingUser, role: e.target.value})}
                  className="w-full px-3 py-2 border rounded"
                >
                  {Object.keys(roles).map(role => (
                    <option key={role} value={role}>{role}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Projects</label>
                <div className="space-y-1 max-h-32 overflow-auto border rounded p-2">
                  {projects.map(project => (
                    <label key={project} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={editingUser.projects?.includes(project)}
                        onChange={(e) => {
                          const userProjects = editingUser.projects || [];
                          if (e.target.checked) {
                            setEditingUser({
                              ...editingUser,
                              projects: [...userProjects, project]
                            });
                          } else {
                            setEditingUser({
                              ...editingUser,
                              projects: userProjects.filter(p => p !== project)
                            });
                          }
                        }}
                        className="mr-2"
                      />
                      <span className="text-sm">{project.replace('_', ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={editingUser.active}
                    onChange={(e) => setEditingUser({...editingUser, active: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm">Active</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <button
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 text-gray-600 border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => updateUser(editingUser.username, {
                  email: editingUser.email,
                  role: editingUser.role,
                  projects: editingUser.projects,
                  active: editingUser.active
                })}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPanel;

