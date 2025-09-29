import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const ProjectDashboard = () => {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadProject = async () => {
      try {
        const response = await fetch(`/api/projects/${id}`);
        if (!response.ok) {
          throw new Error(`Failed to load project (${response.status})`);
        }

        const data = await response.json();
        if (isMounted) {
          setProject(data);
        }
      } catch (projectError) {
        console.error("Failed to load project", projectError);
        if (isMounted) {
          setError("Unable to load project details.");
        }
      }
    };

    loadProject();

    return () => {
      isMounted = false;
    };
  }, [id]);

  if (error) {
    return <p>{error}</p>;
  }

  if (!project) {
    return <p>Loading project…</p>;
  }

  return (
    <div className="project-dashboard">
      <h1>Project {project.id}: {project.name}</h1>
      <p>Drive ID: {project.drive_id}</p>
      <p>Created: {new Date(project.created_at).toLocaleString()}</p>
    </div>
  );
};

export default ProjectDashboard;
