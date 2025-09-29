import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [category, setCategory] = useState("all");
  const [projectId, setProjectId] = useState("all");
  const [user, setUser] = useState({ role: "", projects: [] });

  useEffect(() => {
    fetch("/api/users/me")
      .then((response) => response.json())
      .then((data) => setUser(data))
      .catch((error) => console.error("Failed to fetch user", error));
  }, []);

  useEffect(() => {
    fetch("/api/alerts/recent")
      .then((response) => response.json())
      .then((data) => {
        setAlerts(Array.isArray(data) ? data : []);
      })
      .catch((error) => console.error("Failed to fetch alerts", error));
  }, []);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      const categoryMatches = category === "all" || alert.level === category;
      const projectMatches =
        projectId === "all" || String(alert.project_id) === String(projectId);

      return categoryMatches && projectMatches;
    });
  }, [alerts, category, projectId]);

  return (
    <div className="p-4 bg-white shadow rounded-lg h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-3">⚠️ Alerts</h2>
      <div className="flex gap-2 mb-3">
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="all">All</option>
          <option value="warning">Warnings</option>
          <option value="info">Info</option>
          <option value="error">Errors</option>
        </select>
        <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
          <option value="all">All Projects</option>
          {user.projects.map((pid) => (
            <option key={pid} value={pid}>
              Project {pid}
            </option>
          ))}
        </select>
      </div>
      <ul className="space-y-2">
        {filteredAlerts.map((alert, index) => (
          <li
            key={`${alert.message}-${index}`}
            className={`alert-card alert-${alert.level ?? "info"}`}
          >
            <div>{alert.message}</div>
            {alert.project_id && alert.project_id !== 0 && (
              <Link to={`/projects/${alert.project_id}`} className="text-blue-600 underline">
                View Project
              </Link>
            )}
          </li>
        ))}
        {filteredAlerts.length === 0 && <li>No alerts to display.</li>}
      </ul>
    </div>
  );
}

export default AlertsPanel;
