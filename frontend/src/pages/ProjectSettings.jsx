import { useEffect, useState } from "react";

export default function ProjectSettings({ projectId }) {
  const [project, setProject] = useState(null);
  const [name, setName] = useState("");

  useEffect(() => {
    if (projectId) {
      fetch(`/api/projects/${projectId}/settings`).then(r => r.json()).then(data => {
        setProject(data);
        setName(data.name);
      });
    }
  }, [projectId]);

  const save = async () => {
    await fetch(`/api/projects/${projectId}/settings?name=${encodeURIComponent(name)}`, { method: "PUT" });
    alert("Updated project name!");
  };

  if (!projectId) return <div className="p-4">Select a project first</div>;

  return (
    <div className="p-4">
      <h1 className="font-bold text-lg mb-4">Project Settings</h1>
      <input className="border p-1 mr-2" value={name} onChange={e=>setName(e.target.value)}/>
      <button className="border px-3 py-1" onClick={save}>Save</button>
    </div>
  );
}