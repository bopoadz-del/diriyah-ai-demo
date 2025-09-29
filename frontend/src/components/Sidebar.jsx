import { useEffect, useMemo, useState } from "react";

export default function Sidebar({ project, setProject, setSelectedChat, setView }) {
  const [projects, setProjects] = useState([]);
  const [chats, setChats] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    fetch("/api/projects/sync_drive").then(r => r.json()).then(setProjects);
  }, []);

  useEffect(() => {
    const sticky = localStorage.getItem("selectedProjectId");
    if (sticky) {
      const p = projects.find(x => String(x.id) === String(sticky));
      if (p) setProject(p);
    }
  }, [projects]);

  useEffect(() => {
    if (project?.id) {
      localStorage.setItem("selectedProjectId", project.id);
      fetch(`/api/projects/${project.id}/chats`).then(r => r.json()).then(setChats);
    } else {
      setChats([]);
    }
  }, [project]);

  const filtered = useMemo(() => {
    const term = q.toLowerCase();
    return chats
      .filter(c => !term || (c.title || "").toLowerCase().includes(term))
      .sort((a, b) => (a.pinned === b.pinned ? new Date(b.created_at) - new Date(a.created_at) : (a.pinned ? -1 : 1)));
  }, [chats, q]);

  const groups = useMemo(() => {
    const by = { Pinned: [], Today: [], "This week": [], Older: [] };
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfWeek = new Date(startOfToday); startOfWeek.setDate(startOfWeek.getDate() - startOfToday.getDay());
    filtered.forEach(c => {
      const d = new Date(c.created_at || 0);
      const bucket = c.pinned ? "Pinned" : (d >= startOfToday ? "Today" : d >= startOfWeek ? "This week" : "Older");
      by[bucket].push(c);
    });
    return by;
  }, [filtered]);

  const Section = ({ title, items }) => !items.length ? null : (
    <>
      <div className="mt-3 mb-1 text-xs uppercase text-gray-500">{title}</div>
      <ul>
        {items.map(c => (
          <li key={c.id} className="p-1 rounded hover:bg-gray-200 flex items-center justify-between">
            <span
              className="cursor-pointer"
              onClick={() => { setSelectedChat(c.id); setView("chat"); }}
              title={new Date(c.created_at).toLocaleString()}
            >
              {c.title} {c.pinned ? "📌" : ""}
            </span>
            <div className="flex gap-1 text-xs">
              <button title="Rename" onClick={async () => {
                const t = prompt("Rename chat", c.title || "");
                if (!t) return;
                await fetch(`/api/chats/${c.id}/rename?title=${encodeURIComponent(t)}`, { method: "PUT" });
                setChats(prev => prev.map(x => x.id === c.id ? { ...x, title: t } : x));
              }}>✏️</button>
              {c.pinned ? (
                <button title="Unpin" onClick={async () => {
                  await fetch(`/api/chats/${c.id}/unpin`, { method: "PUT" });
                  setChats(prev => prev.map(x => x.id === c.id ? { ...x, pinned: false } : x));
                }}>📌❌</button>
              ) : (
                <button title="Pin" onClick={async () => {
                  await fetch(`/api/chats/${c.id}/pin`, { method: "PUT" });
                  setChats(prev => prev.map(x => x.id === c.id ? { ...x, pinned: true } : x));
                }}>📌</button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  );

  return (
    <div className="w-72 bg-gray-100 p-4 flex flex-col">
      <img src="/masterise-logo.png" alt="Masterise Logo" className="h-12 mb-4" />

      <select
        value={project?.id || ""}
        onChange={e => {
          const p = projects.find(x => String(x.id) === e.target.value);
          setProject(p || null);
        }}
        className="w-full mb-2 border p-2"
      >
        <option value="">Select Project</option>
        {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>

      <input
        className="w-full mb-3 border p-2"
        placeholder="Search chats…"
        value={q}
        onChange={e => setQ(e.target.value)}
      />

      <div className="flex-1 overflow-auto">
        <Section title="Pinned" items={groups.Pinned} />
        <Section title="Today" items={groups.Today} />
        <Section title="This week" items={groups["This week"]} />
        <Section title="Older" items={groups.Older} />
      </div>

      <div className="mt-3 flex flex-col gap-2">
        <button onClick={() => setView("admin")} className="border p-1">Admin</button>
        <button onClick={() => setView("metrics")} className="border p-1">Metrics</button>
        <button onClick={() => setView("settings")} className="border p-1">Project Settings</button>
      </div>
    </div>
  );
}