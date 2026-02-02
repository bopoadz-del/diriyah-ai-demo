import React from "react";
import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";
import SidebarNav from "../components/SidebarNav";

export default function SplitLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-gray-900">
      <Navbar />
      <div className="flex">
        <SidebarNav />
        <main className="flex-1" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
