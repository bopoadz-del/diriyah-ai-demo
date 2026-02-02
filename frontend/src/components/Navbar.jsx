import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "Chat", path: "/chat" },
  { label: "Analytics", path: "/analytics" },
  { label: "Settings", path: "/settings" },
];

export default function Navbar() {
  return (
    <header className="border-b border-gray-200 bg-white/95">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div className="text-lg font-semibold text-gray-900">Diriyah Brain</div>
        <nav className="flex flex-wrap items-center gap-3 text-sm" aria-label="Primary">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `rounded-full px-3 py-1 font-medium transition ${
                  isActive ? "bg-[#a67c52]/10 text-[#a67c52]" : "text-gray-600 hover:bg-gray-100"
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
