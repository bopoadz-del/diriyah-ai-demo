import React from "react";
import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";

export default function SplitLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-6 lg:flex-row">
        <Sidebar />
        <main className="flex-1 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          {children}
        </main>
      </div>
    </div>
  );
}
