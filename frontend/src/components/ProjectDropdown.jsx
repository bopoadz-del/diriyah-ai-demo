import React, { useEffect, useState } from "react";

const ProjectDropdown = ({ onSelect }) => {
  const [projects, setProjects] = useState([]);
  const [active, setActive] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadProjects = async () => {
      try {
        const response = await fetch("/api/projects/scan-drive");
        if (!response.ok) {
          throw new Error(`Scan failed (${response.status})`);
        }

        const data = await response.json();
        if (isMounted) {
          setProjects(Array.isArray(data.projects) ? data.projects : []);
        }
      } catch (scanError) {
        console.error("Failed to scan drive", scanError);
        if (isMounted) {
          setError("Unable to load projects from Drive.");
        }
      }
    };

    loadProjects();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleChange = (event) => {
    const project = event.target.value;
    setActive(project);
    if (project) {
      onSelect?.(project);
    }
  };

  return (
    <div className="project-dropdown">
      <select
        value={active}
        onChange={handleChange}
        className="w-full border border-gray-300 rounded p-2"
      >
        <option value="">Select Project</option>
        {projects.map((projectName) => (
          <option key={projectName} value={projectName}>
            {projectName}
          </option>
        ))}
      </select>
      {error && <p className="project-dropdown-error">{error}</p>}
    </div>
  );
};

export default ProjectDropdown;
