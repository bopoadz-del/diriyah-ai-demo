import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

function ProjectDashboard() {
  const { id } = useParams();
  const [project, setProject] = useState(null);

  useEffect(() => {
    fetch(`/api/projects/${id}`).then(res => res.json()).then(data => setProject(data));
  }, [id]);

  if (!project) return <div>Loading...</div>;
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Project {project.id}: {project.name}</h1>
      <p>Drive ID: {project.drive_id}</p>
      <p>Created: {new Date(project.created_at).toLocaleString()}</p>
    </div>
  );
}
export default ProjectDashboard;
