import { useMemo } from "react";

import Chat from "./Chat";
import Analytics from "./Analytics";
import AlertsPanel from "./AlertsPanel";
import ProjectDashboard from "./ProjectDashboard";
import Settings from "./Settings";
import SplitLayout from "./SplitLayout";

export default function ChatWindow({ project, selectedChat, view, setView, user }) {
  const rightRail = useMemo(() => [
    <ProjectDashboard key="project" project={project} />,
    <AlertsPanel key="alerts" />,
  ], [project]);

  if (view === "metrics") {
    return (
      <div className="flex-1 overflow-y-auto px-8 py-6">
        <Analytics project={project} />
      </div>
    );
  }

  if (view === "settings" || view === "admin") {
    return (
      <div className="flex-1 overflow-y-auto px-8 py-6">
        <Settings user={user} />
      </div>
    );
  }

  return (
    <SplitLayout
      left={
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Active conversation</p>
              <h2 className="text-lg font-semibold text-slate-900">
                {selectedChat ? `Chat #${selectedChat}` : "Select a chat to begin"}
              </h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <button
                className="px-3 py-1 rounded-full border border-slate-200 hover:bg-slate-50"
                onClick={() => setView("metrics")}
              >
                View analytics
              </button>
              <button
                className="px-3 py-1 rounded-full border border-slate-200 hover:bg-slate-50"
                onClick={() => setView("settings")}
              >
                Workspace settings
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <Chat project={project} chat={selectedChat} />
          </div>
        </div>
      }
      right={rightRail}
    />
  );
}
