import React from 'react';
import { Lock, AlertTriangle } from 'lucide-react';

export default function AccessDenied({ reason, resource, action }) {
  const handleRequestAccess = () => {
    console.log('Request access for:', { resource, action });
  };

  return (
    <div className="flex min-h-[400px] items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-8 shadow-sm">
          <div className="mb-4 flex items-center justify-center">
            <div className="rounded-full bg-red-100 p-4">
              <Lock className="h-12 w-12 text-red-600" />
            </div>
          </div>
          
          <div className="text-center">
            <h2 className="mb-2 text-2xl font-semibold text-gray-800">
              Access Denied
            </h2>
            
            <div className="mb-4 flex items-center justify-center gap-2 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4" />
              <span>{reason || 'You do not have permission to access this resource'}</span>
            </div>
            
            {resource && (
              <div className="mb-2 text-sm text-gray-600">
                <span className="font-medium">Resource:</span> {resource}
              </div>
            )}
            
            {action && (
              <div className="mb-6 text-sm text-gray-600">
                <span className="font-medium">Action:</span> {action}
              </div>
            )}
            
            <button
              onClick={handleRequestAccess}
              className="w-full rounded-full bg-[#a67c52] px-6 py-3 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
            >
              Request Access
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
