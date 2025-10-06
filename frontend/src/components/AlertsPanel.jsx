import React from "react";

const mockAlerts = [
  { id: 1, project: "Falcon", category: "deployment", message: "Prod deployment approved by Layla" },
  { id: 2, project: "Qasr", category: "validation", message: "BoQ variance exceeds threshold" }
];

const AlertsPanel = () => {
  return (
    <aside className="flex h-full flex-col border-l bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-gray-900">Live Alerts</h2>
        <p className="text-xs text-gray-500">Updates are pushed from the approvals workflow.</p>
      </div>
      <div className="flex-1 overflow-auto px-4 py-3 space-y-3">
        {mockAlerts.map((alert) => (
          <div key={alert.id} className="rounded-md border border-amber-200 bg-amber-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">{alert.category}</p>
            <p className="text-sm text-gray-900">{alert.message}</p>
            <p className="text-xs text-gray-500">Project {alert.project}</p>
          </div>
        ))}
      </div>
    </aside>
  );
};

export default AlertsPanel;
