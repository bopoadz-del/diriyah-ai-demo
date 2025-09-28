import React, { useState, useEffect } from "react";
const ProjectDropdown = ({ onSelect }) => {
  const [projects, setProjects] = useState([]);
  const [active, setActive] = useState("");
  useEffect(() => { fetch("/api/projects/scan-drive").then((res) => res.json()).then((data) => setProjects(data.projects)); }, []);
  const handleChange = (e) => { const project = e.target.value; setActive(project); onSelect(project); };
  return (
    <select value={active} onChange={handleChange} className="w-full border border-gray-300 rounded p-2">
      <option value="">Select Project</option>
      {projects.map((p, idx) => (<option key={idx} value={p}>{p}</option>))}
    </select>
  );
};
export default ProjectDropdown;
