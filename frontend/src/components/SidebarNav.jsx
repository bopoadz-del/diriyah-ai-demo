import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "Chat", path: "/chat" },
  { label: "Analytics", path: "/analytics" },
  { label: "Settings", path: "/settings" },
];

export default function SidebarNav() {
  return (
    <aside className="hidden w-64 flex-shrink-0 border-r border-gray-200 bg-white/95 p-6 md:block">
      <div className="text-sm font-semibold uppercase tracking-wide text-gray-400">Navigation</div>
      <nav className="mt-4 space-y-1" aria-label="Primary">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `block rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive ? "bg-[#a67c52]/10 text-[#a67c52]" : "text-gray-600 hover:bg-gray-100"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
