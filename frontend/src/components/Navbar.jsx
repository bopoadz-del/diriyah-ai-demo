import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Chat", to: "/chat" },
  { label: "Analytics", to: "/analytics" },
  { label: "Settings", to: "/settings" },
];

export default function Navbar() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Diriyah Brain</p>
          <h1 className="text-lg font-semibold text-gray-900">Project Control Center</h1>
        </div>
        <nav className="hidden items-center gap-4 text-sm font-medium text-gray-600 md:flex" aria-label="Top">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-full px-4 py-2 transition ${
                  isActive
                    ? "bg-[#f5eee6] text-[#8a5b2d]"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
