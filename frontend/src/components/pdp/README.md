# PDP (Policy Decision Point) React Components

This directory contains React components for the Policy Decision Point (PDP) system that manages access control, permissions, and policy enforcement.

## Hooks and Context

### usePDP Hook
Location: `/frontend/src/hooks/usePDP.js`

Custom React hook providing PDP operations for permission checking, access management, rate limiting, and audit trails.

**Returns:**
- `checkPermission(resource, action, userId, context)` - Check if user has permission
- `grantAccess(userId, projectId, role, grantedBy, expiresAt)` - Grant user access
- `revokeAccess(userId, projectId)` - Revoke user access
- `getRateLimit(userId, endpoint)` - Get rate limit status
- `getAuditTrail(filters)` - Get filtered audit logs
- `loading` (boolean) - Loading state
- `error` (Error|null) - Last error

**Usage:**
```jsx
import { usePDP } from '../../hooks/usePDP';

function MyComponent() {
  const { checkPermission, grantAccess, loading, error } = usePDP();
  
  const handleCheck = async () => {
    const decision = await checkPermission('project:123', 'read', userId);
    if (decision.allowed) {
      console.log('Access granted!');
    }
  };
  
  const handleGrant = async () => {
    await grantAccess(userId, projectId, 'viewer', adminId);
  };
}
```

### PDPContext
Location: `/frontend/src/contexts/PDPContext.jsx`

Global React context for managing PDP state across the application.

**Provider Props:**
- `userId` (number, required) - Current user ID
- `projectId` (number, optional) - Current project ID
- `autoRefresh` (boolean, default: true) - Auto-refresh permissions
- `refreshInterval` (number, default: 300000) - Refresh interval in ms

**Context Value:**
- `permissions` (Array) - Cached user permissions
- `rateLimits` (Object) - Cached rate limit statuses
- `loading` (boolean) - Loading state
- `error` (Error|null) - Last error
- `lastRefresh` (Date|null) - Last refresh timestamp
- `refreshPermissions(userId, projectId)` - Refresh permissions
- `hasPermission(permission)` - Check cached permission
- `checkAccess(resource, action, context)` - Live permission check
- `getRateLimitStatus(endpoint)` - Get rate limit status
- `isRateLimitOk(endpoint)` - Check if rate limit allows requests

**Usage:**
```jsx
import { PDPProvider, usePDPContext } from '../../contexts/PDPContext';

// Wrap your app
function App() {
  return (
    <PDPProvider userId={currentUserId} projectId={currentProjectId}>
      <Dashboard />
    </PDPProvider>
  );
}

// Use in child components
function Dashboard() {
  const { hasPermission, checkAccess, permissions } = usePDPContext();
  
  if (!hasPermission('project:read')) {
    return <AccessDenied />;
  }
  
  return <div>Dashboard content</div>;
}
```

## Components

### 1. AccessDenied.jsx
Component displayed when a user's access is denied.

**Props:**
- `reason` (string): Explanation for why access was denied
- `resource` (string): The resource that was attempted to be accessed
- `action` (string): The action that was attempted (read, write, delete, etc.)

**Usage:**
```jsx
import { AccessDenied } from './components/pdp';

<AccessDenied 
  reason="Insufficient permissions" 
  resource="project/123" 
  action="write" 
/>
```

### 2. PermissionsPanel.jsx
Admin panel for managing user permissions on a project.

**Props:**
- `projectId` (string): ID of the project to manage permissions for

**Features:**
- List all users with their roles
- View individual user permissions
- Grant/revoke access for specific resources and actions
- Real-time permission updates

**API Endpoints:**
- `GET /api/pdp/projects/{projectId}/users` - Fetch project users
- `GET /api/pdp/users/{userId}/permissions` - Fetch user permissions
- `POST /api/pdp/access/grant` - Grant access
- `POST /api/pdp/access/revoke` - Revoke access

**Usage:**
```jsx
import { PermissionsPanel } from './components/pdp';

<PermissionsPanel projectId="project-123" />
```

### 3. AuditTrail.jsx
Display audit logs for access control decisions and actions.

**Props:**
- `userId` (string, optional): Filter logs by specific user
- `startDate` (string, optional): Start date for log range (ISO format)
- `endDate` (string, optional): End date for log range (ISO format)

**Features:**
- Filterable table of audit logs
- Filter by action type (read, write, delete)
- Filter by decision (allow, deny)
- Export logs to CSV
- Real-time refresh

**API Endpoints:**
- `GET /api/pdp/audit-trail?user_id={userId}&start_date={startDate}&end_date={endDate}`

**Usage:**
```jsx
import { AuditTrail } from './components/pdp';

<AuditTrail 
  userId="user-123" 
  startDate="2024-01-01T00:00:00Z" 
  endDate="2024-01-31T23:59:59Z" 
/>
```

### 4. RateLimitIndicator.jsx
Visual indicator showing rate limit status for a user and endpoint.

**Props:**
- `userId` (string): User ID to check rate limits for
- `endpoint` (string): API endpoint to check rate limits for

**Features:**
- Progress bar showing remaining requests
- Auto-refresh every 30 seconds
- Visual warnings when limits are approaching
- Shows reset time

**API Endpoints:**
- `GET /api/pdp/rate-limit/{userId}/{endpoint}`

**Usage:**
```jsx
import { RateLimitIndicator } from './components/pdp';

<RateLimitIndicator userId="user-123" endpoint="/api/projects" />
```

### 5. PolicyList.jsx
Admin view displaying all active policies in a card grid.

**Props:**
- `onEdit` (function, optional): Callback when edit button is clicked, receives policy object
- `onCreate` (function, optional): Callback when create button is clicked

**Features:**
- Search policies by name or type
- Toggle policy enabled/disabled status
- Visual indicators for policy priority
- Color-coded policy types
- Refresh functionality

**API Endpoints:**
- `GET /api/pdp/policies` - Fetch all policies
- `PUT /api/pdp/policies/{id}` - Update policy (for toggle)

**Usage:**
```jsx
import { PolicyList } from './components/pdp';

<PolicyList 
  onEdit={(policy) => console.log('Edit:', policy)}
  onCreate={() => console.log('Create new policy')}
/>
```

### 6. PolicyForm.jsx
Form component for creating or editing policies.

**Props:**
- `policy` (object, optional): Existing policy to edit. If not provided, creates new policy
- `onSave` (function, optional): Callback when policy is successfully saved, receives saved policy
- `onCancel` (function, optional): Callback when cancel button is clicked

**Fields:**
- Name (required)
- Description
- Type (RBAC, ABAC, Rate Limit, Custom)
- Priority (0-100)
- Rules (JSON editor)
- Enabled (checkbox)

**API Endpoints:**
- `POST /api/pdp/policies` - Create new policy
- `PUT /api/pdp/policies/{id}` - Update existing policy

**Usage:**
```jsx
import { PolicyForm } from './components/pdp';

// Create new policy
<PolicyForm 
  onSave={(policy) => console.log('Saved:', policy)}
  onCancel={() => console.log('Cancelled')}
/>

// Edit existing policy
<PolicyForm 
  policy={existingPolicy}
  onSave={(policy) => console.log('Updated:', policy)}
  onCancel={() => console.log('Cancelled')}
/>
```

## Common Features

All components include:
- **React Hooks**: Uses `useState` and `useEffect` for state management
- **Error Handling**: Try-catch blocks around all API calls with user-friendly error messages
- **Loading States**: Loading indicators during data fetches
- **Tailwind CSS**: Consistent styling using Tailwind utility classes
- **Lucide Icons**: Modern icons from lucide-react library
- **Responsive Design**: Mobile-friendly layouts

## Styling

The components follow the existing design system:
- Primary color: `#a67c52` (brown/tan)
- Accent background: `#f6efe6` (light beige)
- Standard borders: `border-gray-200`
- Hover states: Opacity changes or background color shifts
- Rounded corners: `rounded-lg` or `rounded-full` for buttons

## API Response Format

Expected API response formats:

### Audit Trail
```json
{
  "logs": [
    {
      "timestamp": "2024-01-28T12:00:00Z",
      "action": "read",
      "resource": "project/123",
      "decision": "allow",
      "reason": "User has read permission"
    }
  ]
}
```

### Rate Limit
```json
{
  "remaining": 45,
  "limit": 100,
  "reset_at": "2024-01-28T13:00:00Z"
}
```

### Policies
```json
{
  "policies": [
    {
      "id": "policy-1",
      "name": "Project Read Access",
      "type": "rbac",
      "rules": { "conditions": [], "effect": "allow" },
      "priority": 80,
      "enabled": true,
      "description": "Allows read access to projects"
    }
  ]
}
```

### User Permissions
```json
{
  "permissions": {
    "project:read": true,
    "project:write": false,
    "document:read": true
  }
}
```

## Dependencies

Required packages (already in package.json):
- `react` ^18.2.0
- `lucide-react` ^0.379.0
- `tailwindcss` ^3.4.10

## Integration Example

Complete example of integrating PDP components into an admin dashboard:

```jsx
import React, { useState } from 'react';
import {
  AccessDenied,
  PermissionsPanel,
  AuditTrail,
  RateLimitIndicator,
  PolicyList,
  PolicyForm,
} from './components/pdp';

function AdminDashboard() {
  const [view, setView] = useState('policies');
  const [editingPolicy, setEditingPolicy] = useState(null);

  return (
    <div className="p-6">
      <nav className="mb-6 flex gap-2">
        <button onClick={() => setView('policies')}>Policies</button>
        <button onClick={() => setView('permissions')}>Permissions</button>
        <button onClick={() => setView('audit')}>Audit Trail</button>
      </nav>

      {view === 'policies' && !editingPolicy && (
        <PolicyList
          onEdit={setEditingPolicy}
          onCreate={() => setEditingPolicy({})}
        />
      )}

      {view === 'policies' && editingPolicy && (
        <PolicyForm
          policy={editingPolicy.id ? editingPolicy : null}
          onSave={() => {
            setEditingPolicy(null);
            // Refresh policy list
          }}
          onCancel={() => setEditingPolicy(null)}
        />
      )}

      {view === 'permissions' && (
        <PermissionsPanel projectId="project-123" />
      )}

      {view === 'audit' && (
        <AuditTrail />
      )}

      <RateLimitIndicator userId="current-user" endpoint="/api/projects" />
    </div>
  );
}
```

## Notes

- Components are designed to work independently and can be used separately or together
- All API endpoints are relative and will use the current host
- Error states are handled gracefully with user-friendly messages
- Components follow React best practices with functional components and hooks
- No PropTypes validation included (can be added if TypeScript is not being used)
