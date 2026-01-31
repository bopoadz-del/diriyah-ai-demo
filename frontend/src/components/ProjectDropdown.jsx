import React, { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

const ProjectDropdown = ({ onSelect }) => {
  const [options, setOptions] = useState([]);
  const [error, setError] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(-1);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiFetch("/api/projects/scan-drive");
        if (!res.ok) throw new Error(`Scan failed (${res.status})`);
        const data = await res.json();
        const projects = Array.isArray(data.projects) ? data.projects : [];
        const normalized = projects.map((project, index) => {
          if (typeof project === "string") {
            return {
              value: project,
              label: project,
              path: "",
              lastModified: "",
              source: "stubbed",
            };
          }

          const label = project.name || project.path || `Project ${index + 1}`;
          const lastModified =
            project.last_modified || project.lastModified || "";

          return {
            value: project.name || label,
            label,
            path: project.path || "",
            lastModified,
            source: project.source || "stubbed",
          };
        });
        setOptions(normalized);
        setSelectedIndex(-1);
      } catch (e) {
        console.error("Failed to scan drive", e);
        setError("Unable to scan drive for project folders.");
      }
    };
    load();
  }, []);

  return (
    <div className="project-dropdown">
      <select
        onChange={(e) => {
          const index = e.target.selectedIndex - 1;
          setSelectedIndex(index);
          const option = options[index];
          onSelect?.(option ? option.value : "");
        }}
        value={selectedIndex >= 0 ? options[selectedIndex]?.value : ""}
      >
        <option value="" disabled>Select a Drive project…</option>
        {options.map((option) => (
          <option key={option.value} value={option.value} title={option.path}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="project-dropdown-error">{error}</p>}
      {!error && selectedIndex >= 0 && options[selectedIndex] && (
        <div className="project-dropdown-debug">
          <p><strong>Path:</strong> {options[selectedIndex].path || "Unknown"}</p>
          {options[selectedIndex].lastModified && (
            <p>
              <strong>Last Modified:</strong>{" "}
              {new Date(options[selectedIndex].lastModified).toLocaleString()}
            </p>
          )}
          <p><strong>Source:</strong> {options[selectedIndex].source}</p>
        </div>
      )}
    </div>
  );
};

export default ProjectDropdown;
