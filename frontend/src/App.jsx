import { useEffect, useMemo, useState } from "react";
import "./App.css";
import Sidebar from "./components/Sidebar.jsx";
import Chat from "./components/Chat.jsx";
import ProjectDashboard from "./components/ProjectDashboard.jsx";
import Analytics from "./components/Analytics.jsx";
import AlertsPanel from "./components/AlertsPanel.jsx";
import Settings from "./components/Settings.jsx";

const DEFAULT_VIEW = "chat";

export default function App() {
  const [project, setProject] = useState(null);
  const [selectedChat, setSelectedChat] = useState(null);
  const [view, setView] = useState(DEFAULT_VIEW);
  const [contextStatus, setContextStatus] = useState("idle");

  useEffect(() => {
    if (!project?.id) {
      setSelectedChat(null);
      setContextStatus("idle");
      return;
    }

    let cancelled = false;
    const applyContext = async () => {
      setContextStatus("loading");
      try {
        const response = await fetch(`/api/projects/${project.id}/context`, { method: "POST" });
        if (!response.ok) {
          throw new Error(`Failed to set project context: ${response.status}`);
        }
        if (!cancelled) {
          setContextStatus("ready");
        }
      } catch (error) {
        console.error("Unable to set project context", error);
        if (!cancelled) {
          setContextStatus("error");
        }
      }
    };

    applyContext();
    return () => {
      cancelled = true;
    };
  }, [project?.id]);

  useEffect(() => {
    setView(DEFAULT_VIEW);
  }, [project?.id]);

  const headerSubtitle = useMemo(() => {
    if (contextStatus === "loading") return "Syncing project context…";
    if (contextStatus === "error") return "Context sync failed. Chat actions may be limited.";
    if (!project?.name) return "Select a project from the sidebar to begin.";
    return project.summary || "Choose a chat to analyse project activity.";
  }, [contextStatus, project]);

  const mainContent = useMemo(() => {
    switch (view) {
      case "metrics":
        return (
          <div className="main-panel">
            <Analytics projectId={project?.id} />
            <AlertsPanel projectId={project?.id} className="mt-4" />
          </div>
        );
      case "settings":
        return (
          <div className="main-panel">
            <Settings activeProjectId={project?.id} />
          </div>
        );
      case "admin":
        return (
          <div className="main-panel">
            <ProjectDashboard project={project} />
          </div>
        );
      case "chat":
      default:
        return (
          <div className="main-panel">
            <div className="chat-layout">
              <div className="chat-column">
                <Chat project={project} chat={selectedChat} />
              </div>
              <aside className="insights-column">
                <ProjectDashboard project={project} />
                <AlertsPanel projectId={project?.id} />
              </aside>
            </div>
          </div>
        );
    }
  }, [project, selectedChat, view]);

  return (
    <div className="app-shell">
      <Sidebar
        project={project}
        setProject={setProject}
        setSelectedChat={setSelectedChat}
        setView={setView}
      />

      <main className="content-shell">
        <header className="content-header">
          <div>
            <h1 className="title">Diriyah Brain AI</h1>
            <p className="subtitle">{headerSubtitle}</p>
          </div>
          <div className="view-tabs">
            {[
              { id: "chat", label: "Chat" },
              { id: "admin", label: "Project" },
              { id: "metrics", label: "Metrics" },
              { id: "settings", label: "Settings" },
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                className={tab.id === view ? "tab active" : "tab"}
                onClick={() => setView(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </header>

        {mainContent}
      </main>
    </div>
  );
}
