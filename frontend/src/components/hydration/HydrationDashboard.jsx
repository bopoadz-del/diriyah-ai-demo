import React, { useState } from "react";
import { useHydration } from "../../hooks/useHydration";

const formatDate = (value) => (value ? new Date(value).toLocaleString() : "-");

const StatusCard = ({ title, value }) => (
  <div className="bg-white rounded-lg shadow p-4">
    <p className="text-sm text-gray-500">{title}</p>
    <p className="text-lg font-semibold text-gray-900">{value}</p>
  </div>
);

export default function HydrationDashboard({ workspaceId }) {
  const { status, runs, alerts, sources, loading, error, runNow, reload } = useHydration(workspaceId);
  const [runningNow, setRunningNow] = useState(false);

  const handleRunNow = async () => {
    setRunningNow(true);
    try {
      await runNow();
      await reload();
    } finally {
      setRunningNow(false);
    }
  };

  if (!workspaceId) {
    return <div className="p-6">Select a workspace to view hydration.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Hydration Dashboard</h1>
          <p className="text-sm text-gray-500">Workspace: {workspaceId}</p>
        </div>
        <button
          type="button"
          onClick={handleRunNow}
          className="px-4 py-2 rounded-md bg-emerald-600 text-white disabled:opacity-50"
          disabled={runningNow}
        >
          {runningNow ? "Running..." : "Run Now"}
        </button>
      </div>

      {error && <div className="text-red-600">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusCard title="Status" value={status?.status || "unknown"} />
        <StatusCard title="Last Run" value={formatDate(status?.last_run_at)} />
        <StatusCard title="Next Run" value={formatDate(status?.next_run_at)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">Recent Runs</h2>
          {loading && <p className="text-sm text-gray-500">Loading...</p>}
          {!loading && runs.length === 0 && <p className="text-sm text-gray-500">No runs yet.</p>}
          <div className="space-y-3">
            {runs.map((run) => (
              <div key={run.id} className="border-b pb-2">
                <div className="flex justify-between text-sm">
                  <span>Run #{run.id}</span>
                  <span className="text-gray-500">{formatDate(run.started_at)}</span>
                </div>
                <div className="text-xs text-gray-500">Status: {run.status}</div>
                <div className="text-xs text-gray-500">
                  Files: {run.files_seen} seen · {run.files_new} new · {run.files_updated} updated · {run.files_failed} failed
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">Active Alerts</h2>
          {alerts.length === 0 && <p className="text-sm text-gray-500">No active alerts.</p>}
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className="border-b pb-2">
                <div className="text-sm font-medium">{alert.severity.toUpperCase()} · {alert.category}</div>
                <div className="text-xs text-gray-500">{alert.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-3">Sources</h2>
        {sources.length === 0 && <p className="text-sm text-gray-500">No sources configured.</p>}
        <div className="space-y-2">
          {sources.map((source) => (
            <div key={source.id} className="flex justify-between text-sm border-b pb-2">
              <div>
                <div className="font-medium">{source.name}</div>
                <div className="text-xs text-gray-500">{source.source_type}</div>
              </div>
              <div className={source.is_enabled ? "text-emerald-600" : "text-gray-400"}>
                {source.is_enabled ? "Enabled" : "Disabled"}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
