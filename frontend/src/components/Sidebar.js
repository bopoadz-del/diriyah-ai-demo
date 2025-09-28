import React, { useEffect, useState } from "react";
const Sidebar = ({ onSelectProject }) => {
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [locked, setLocked] = useState(true);
  useEffect(() => { fetch("/api/projects").then((res) => res.json()).then((data) => setProjects(data)); }, []);
  const handleClick = async (projectId, name) => {
    await fetch(`/api/projects/${projectId}/context`, { method: "POST" });
    setActiveProject(name); onSelectProject(projectId);
  };
  return (
    <div className={`sidebar ${locked ? "locked" : "collapsed"}`}>
      <div className="sidebar-header">
        <h3>Projects</h3>
        <div>
          <button onClick={() => window.location.reload()}>Refresh</button>
          <button onClick={() => setLocked(!locked)}>{locked ? "Unlock" : "Lock"}</button>
        </div>
      </div>
      {locked && (<ul>{projects.map((p) => (
        <li key={p.id} onClick={() => handleClick(p.id, p.name)} className={activeProject === p.name ? "active" : ""}>{p.name}</li>
      ))}</ul>)}
    </div>
  );
};
export default Sidebar;
