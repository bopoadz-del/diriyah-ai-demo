import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Chat", to: "/chat" },
  { label: "Analytics", to: "/analytics" },
  { label: "Settings", to: "/settings" },
];

export default function Sidebar() {
  return (
    <aside className="w-full max-w-xs border-r border-gray-200 bg-white p-6">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Diriyah AI</p>
        <h2 className="text-lg font-semibold text-gray-900">Workspace</h2>
        <p className="mt-1 text-sm text-gray-500">Navigate your delivery overview.</p>
      </div>

      <nav className="space-y-2" aria-label="Primary">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center justify-between rounded-lg px-4 py-3 text-sm font-medium transition ${
                isActive
                  ? "bg-[#f5eee6] text-[#8a5b2d]"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`
            }
          >
            <span>{item.label}</span>
            <span aria-hidden className="text-xs">→</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-10 rounded-xl border border-gray-200 bg-gray-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Next checkpoint</p>
        <p className="mt-2 text-sm font-medium text-gray-900">Executive steering review</p>
        <p className="mt-1 text-xs text-gray-500">Tomorrow · 09:00 AM (GMT+3)</p>
      </div>
    </aside>
  );
}
