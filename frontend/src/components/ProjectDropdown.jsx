import React, { useEffect, useState } from "react";

const ProjectDropdown = ({ onSelect }) => {
  const [options, setOptions] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/projects/scan-drive");
        if (!res.ok) throw new Error(`Scan failed (${res.status})`);
        const data = await res.json();
        setOptions(data.projects || []);
      } catch (e) {
        console.error("Failed to scan drive", e);
        setError("Unable to scan drive for project folders.");
      }
    };
    load();
  }, []);

  return (
    <div className="project-dropdown">
      <select onChange={(e) => onSelect?.(e.target.value)} defaultValue="">
        <option value="" disabled>Select a Drive project…</option>
        {options.map((name) => (<option key={name} value={name}>{name}</option>))}
      </select>
      {error && <p className="project-dropdown-error">{error}</p>}
    </div>
  );
};

export default ProjectDropdown;
