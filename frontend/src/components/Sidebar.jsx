import React from "react";

const projects = ["Villa 100", "Tower 20", "Gateway Villas", "Cultural District"];

const navigationItems = [
  { id: "home", label: "Home" },
  { id: "chat", label: "Chat" },
  { id: "intelligence", label: "Advanced Intelligence" },
  { id: "help", label: "Help" },
  { id: "settings", label: "Settings" },
];

export default function Sidebar({ activePage, onNavigate, activeProject, onSelect }) {
  return (
    <aside className="w-64 bg-[#f5f0e6] border-r border-gray-300 flex flex-col p-6 gap-6">
      <div className="flex flex-col items-center gap-4">
        <img src="/logo.png" alt="Diriyah Logo" className="w-16 h-16" />
        <button
          type="button"
          className="bg-[#a67c52] hover:bg-[#8f6843] transition-colors text-white px-4 py-2 rounded-md w-full text-sm font-semibold"
          onClick={() => onNavigate("chat")}
        >
          + New Chat
        </button>
      </div>

      <div>
        <h4 className="font-bold text-sm uppercase tracking-wide text-gray-700 mb-3">Projects</h4>
        <div className="flex flex-col gap-2">
          {projects.map((project) => (
            <button
              key={project}
              type="button"
              onClick={() => onSelect(project)}
              className={`text-left px-3 py-2 rounded-md transition-colors ${
                activeProject === project ? "bg-white font-semibold shadow-sm" : "hover:bg-white/60"
              }`}
            >
              {project}
            </button>
          ))}
        </div>
      </div>

      <nav className="flex flex-col gap-2 mt-auto">
        {navigationItems.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`text-left px-3 py-2 rounded-md transition-colors ${
              activePage === item.id ? "bg-white font-semibold shadow-sm" : "hover:bg-white/60"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="pt-4 border-t border-gray-300 flex items-center gap-3">
        <div className="bg-gray-500 text-white w-10 h-10 rounded-full flex items-center justify-center font-semibold">K</div>
        <div className="leading-tight">
          <p className="font-semibold text-gray-900">Khalid</p>
          <p className="text-xs text-gray-600">Engineer</p>
        </div>
      </div>
    </aside>
  );
}
