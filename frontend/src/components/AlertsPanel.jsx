import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [category, setCategory] = useState("all");
  const [projectId, setProjectId] = useState("all");
  const [user, setUser] = useState({ role: "", projects: [] });

  useEffect(() => {
    fetch("/api/users/me").then(res => res.json()).then(data => setUser(data));
  }, []);

  const fetchAlerts = () => {
    let url = "/api/alerts?";
    if (category !== "all") url += `category=${category}&`;
    if (projectId !== "all") url += `project_id=${projectId}&`;
    fetch(url).then(res => res.json()).then(data => setAlerts(data.alerts || []));
  };

  useEffect(() => { if (user.role) fetchAlerts(); }, [category, projectId, user]);

  return (
    <div className="p-4 bg-white shadow rounded-lg h-full overflow-y-auto">
      <h2 className="text-xl font-bold mb-3">⚠️ Alerts</h2>
      <div className="flex gap-2 mb-3">
        <select value={category} onChange={e => setCategory(e.target.value)}>
          <option value="all">All</option>
          <option value="deployment">Deployment</option>
          <option value="compliance">Compliance</option>
          <option value="analytics">Analytics</option>
        </select>
        <select value={projectId} onChange={e => setProjectId(e.target.value)}>
          <option value="all">All Projects</option>
          {user.projects.map(pid => <option key={pid} value={pid}>Project {pid}</option>)}
        </select>
      </div>
      {alerts.map((a) => (
        <li key={a.id} className={a.category==="deployment" ? "bg-red-50" : "bg-yellow-50"}>
          <div>{a.message}</div>
          {a.project_id && a.project_id !== 0 && (
            <Link to={`/projects/${a.project_id}`} className="text-blue-600 underline">View Project</Link>
          )}
        </li>
      ))}
    </div>
  );
}
export default AlertsPanel;
