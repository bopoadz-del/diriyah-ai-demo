import { useEffect, useMemo, useState } from "react";

const FALLBACK_PROJECTS = [
  {
    id: "dg-001",
    name: "Diriyah Gate Cultural District",
    status: "In Progress",
    location: "Diriyah, Riyadh",
    progress_percent: 68,
  },
  {
    id: "dg-002",
    name: "Diriyah Wadi Enhancement",
    status: "Design Development",
    location: "Wadi Hanifah, Diriyah",
    progress_percent: 42,
  },
  {
    id: "dg-003",
    name: "Bujairi Terrace Expansion",
    status: "Construction",
    location: "Bujairi, Diriyah",
    progress_percent: 81,
  },
];

function buildChatFixtures(project) {
  const now = new Date();
  return [
    {
      id: `${project.id}-overview`,
      title: `${project.name.split(" ")[0]} executive summary`,
      pinned: true,
      created_at: now.toISOString(),
    },
    {
      id: `${project.id}-qa`,
      title: "RFI triage",
      pinned: false,
      created_at: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: `${project.id}-safety`,
      title: "Weekly safety review",
      pinned: false,
      created_at: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];
}

export default function Sidebar({ project, selectedChat, setProject, setSelectedChat, setView }) {
  const [projects, setProjects] = useState([]);
  const [chats, setChats] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const loadProjects = async () => {
      try {
        const res = await fetch("/api/projects");
        if (!res.ok) throw new Error(`projects failed: ${res.status}`);
        const payload = await res.json();
        if (!cancelled) {
          setProjects(payload.projects || FALLBACK_PROJECTS);
          setError("");
        }
      } catch (err) {
        console.warn("Failed to load project catalogue", err);
        if (!cancelled) {
          setProjects(FALLBACK_PROJECTS);
          setError("Offline – using fixture projects");
        }
      }
    };
    loadProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!projects.length) return;
    const sticky = localStorage.getItem("selectedProjectId");
    if (sticky) {
      const pinnedProject = projects.find((item) => String(item.id) === sticky);
      if (pinnedProject) {
        setProject(pinnedProject);
      }
    }
  }, [projects, setProject]);

  useEffect(() => {
    if (!project?.id) {
      setChats([]);
      return;
    }
    localStorage.setItem("selectedProjectId", String(project.id));
    const fixtures = buildChatFixtures(project);
    setChats(fixtures);
    setSelectedChat((current) => current ?? fixtures[0]?.id ?? null);
  }, [project, setSelectedChat]);

  const filteredChats = useMemo(() => {
    const term = query.trim().toLowerCase();
    return chats
      .filter((chat) =>
        !term ? true : (chat.title || "").toLowerCase().includes(term) || String(chat.id).toLowerCase().includes(term),
      )
      .sort((a, b) => {
        if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [chats, query]);

  const groups = useMemo(() => {
    const bucketed = { Pinned: [], Today: [], "This week": [], Older: [] };
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfWeek = new Date(startOfToday);
    startOfWeek.setDate(startOfWeek.getDate() - startOfToday.getDay());

    filteredChats.forEach((chat) => {
      const created = new Date(chat.created_at || 0);
      let bucket = "Older";
      if (chat.pinned) bucket = "Pinned";
      else if (created >= startOfToday) bucket = "Today";
      else if (created >= startOfWeek) bucket = "This week";
      bucketed[bucket].push(chat);
    });
    return bucketed;
  }, [filteredChats]);

  const renderSection = (title, items) => {
    if (!items.length) return null;
    return (
      <div key={title} className="mt-4">
        <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">{title}</div>
        <ul className="space-y-1">
          {items.map((chat) => (
            <li
              key={chat.id}
              className={`flex items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-white/70 ${
                chat.id === selectedChat ? "bg-white/70" : ""
              }`}
            >
              <button
                className="flex-1 text-left"
                onClick={() => {
                  setSelectedChat(chat.id);
                  setView("chat");
                }}
              >
                <span className="font-medium text-slate-800">{chat.title}</span>
                <div className="text-xs text-slate-500">
                  {new Date(chat.created_at).toLocaleString()} {chat.pinned ? "· Pinned" : ""}
                </div>
              </button>
              <button
                className="ml-2 text-xs text-slate-400 hover:text-slate-600"
                onClick={() =>
                  setChats((prev) =>
                    prev.map((item) =>
                      item.id === chat.id ? { ...item, pinned: !item.pinned } : item,
                    ),
                  )
                }
                title={chat.pinned ? "Unpin chat" : "Pin chat"}
              >
                {chat.pinned ? "📌" : "📍"}
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <aside className="w-72 shrink-0 border-r border-slate-200 bg-white/80 backdrop-blur px-5 py-6 flex flex-col gap-4">
      <div>
        <img src="/masterise-logo.png" alt="Masterise Logo" className="h-12" />
        <p className="mt-2 text-xs uppercase tracking-[0.4em] text-slate-500">Command centre</p>
      </div>

      <div>
        <label className="text-xs font-semibold text-slate-500">Project</label>
        <select
          value={project?.id || ""}
          onChange={(event) => {
            const nextProject = projects.find((item) => String(item.id) === event.target.value);
            setProject(nextProject ?? null);
          }}
          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
        >
          <option value="" disabled>
            Select project…
          </option>
          {projects.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        {error && <p className="mt-2 text-xs text-amber-600">{error}</p>}
      </div>

      <div>
        <input
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
          placeholder="Search chats"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {renderSection("Pinned", groups.Pinned)}
        {renderSection("Today", groups.Today)}
        {renderSection("This week", groups["This week"])}
        {renderSection("Older", groups.Older)}
      </div>

      <div className="space-y-2 text-sm">
        <button
          onClick={() => setView("chat")}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left hover:bg-white/70"
        >
          💬 Conversation
        </button>
        <button
          onClick={() => setView("metrics")}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left hover:bg-white/70"
        >
          📊 Analytics
        </button>
        <button
          onClick={() => setView("settings")}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left hover:bg-white/70"
        >
          ⚙️ Workspace settings
        </button>
      </div>
    </aside>
  );
}
