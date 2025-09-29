import React, { useCallback, useEffect, useState } from "react";
import ProjectDropdown from "./ProjectDropdown";

const Sidebar = ({ onSelectProject }) => {
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [locked, setLocked] = useState(true);
  const [error, setError] = useState("");

  const fetchProjects = useCallback(async () => {
    try {
      const response = await fetch("/api/projects");
      if (!response.ok) throw new Error(`Failed to fetch projects (${response.status})`);
      const data = await response.json();
      setProjects(Array.isArray(data) ? data : []);
      setError("");
    } catch (projectError) {
      console.error("Failed to fetch projects", projectError);
      setError("Unable to load projects.");
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleClick = async (projectId, projectName) => {
    try {
      await fetch(`/api/projects/${projectId}/context`, { method: "POST" });
      setActiveProjectId(projectId);
      onSelectProject?.(projectId, projectName);
    } catch (contextError) {
      console.error("Failed to set project context", contextError);
      setError("Unable to activate project context.");
    }
  };

  return (
    <div className={`sidebar ${locked ? "locked" : "collapsed"}`}>
      <div className="sidebar-header">
        <h3>Projects</h3>
        <div className="sidebar-actions">
          <button type="button" onClick={fetchProjects}>Refresh</button>
          <button type="button" onClick={() => setLocked((prev) => !prev)}>{locked ? "Unlock" : "Lock"}</button>
        </div>
      </div>

      {locked && (
        <>
          <ProjectDropdown onSelect={(projectName) => { setActiveProjectId(null); onSelectProject?.(null, projectName); }} />
          <ul>
            {projects.map((project) => (
              <li key={project.id} className={activeProjectId === project.id ? "active" : ""} onClick={() => handleClick(project.id, project.name)}>
                {project.name}
              </li>
            ))}
          </ul>
        </>
      )}

      {error && <p className="sidebar-error">{error}</p>}
    </div>
  );
};
export default Sidebar;
