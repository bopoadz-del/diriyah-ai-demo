import React from "react";

const pageTitles = {
  home: "Home",
  chat: "Chat",
  intelligence: "Advanced Intelligence",
  help: "Help & FAQ",
  settings: "Settings",
};

export default function Header({ project, activePage }) {
  const title = pageTitles[activePage] ?? "Diriyah Brain AI";

  return (
    <header className="bg-white/90 border-b border-gray-200 backdrop-blur-sm">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
          <p className="text-sm text-gray-600">Currently viewing: {project}</p>
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <span className="inline-flex h-3 w-3 rounded-full bg-green-500" aria-hidden />
          <span>Connected</span>
        </div>
      </div>
    </header>
  );
}
