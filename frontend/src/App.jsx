import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import Chat from "./components/Chat";
import Admin from "./pages/Admin";
import Metrics from "./pages/Metrics";
import ProjectSettings from "./pages/ProjectSettings";
import "./App.css";

const DEFAULT_VIEW = "chat";

export default function App() {
  const [project, setProject] = useState(null);
  const [selectedChat, setSelectedChat] = useState(null);
  const [view, setView] = useState(DEFAULT_VIEW);
  const [creatingChat, setCreatingChat] = useState(false);
  const [error, setError] = useState("");
  const [refreshChatsToken, setRefreshChatsToken] = useState(0);

  useEffect(() => {
    setSelectedChat(null);
    setView(DEFAULT_VIEW);
  }, [project?.id]);

  const handleCreateChat = async () => {
    if (!project?.id || creatingChat) {
      return;
    }

    try {
      setCreatingChat(true);
      setError("");

      const response = await fetch(`/api/projects/${project.id}/chats`, { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to create a new chat at the moment.");
      }

      const chat = await response.json();
      setSelectedChat(chat.id);
      setView(DEFAULT_VIEW);
      setRefreshChatsToken(token => token + 1);
    } catch (err) {
      setError(err.message || "Something went wrong while creating a chat.");
    } finally {
      setCreatingChat(false);
    }
  };

  const renderContent = () => {
    if (view === "admin") {
      return <Admin />;
    }

    if (view === "metrics") {
      return <Metrics />;
    }

    if (view === "settings") {
      return <ProjectSettings projectId={project?.id} />;
    }

    if (!project?.id) {
      return (
        <div className="app-empty-state">
          <p className="app-empty-title">Select a project to get started</p>
          <p className="app-empty-subtitle">
            Choose a project from the left panel to explore chats, metrics, and settings.
          </p>
        </div>
      );
    }

    if (!selectedChat) {
      return (
        <div className="app-empty-state">
          <p className="app-empty-title">No chat selected</p>
          <p className="app-empty-subtitle">Pick an existing conversation or create a new chat to begin.</p>
        </div>
      );
    }

    return <Chat project={project} chat={selectedChat} />;
  };

  return (
    <div className="app-shell">
      <Sidebar
        project={project}
        setProject={setProject}
        setSelectedChat={setSelectedChat}
        setView={setView}
        refreshChatsToken={refreshChatsToken}
      />
      <div className="app-main">
        <header className="app-header">
          <div>
            <h1 className="app-title">Diriyah AI Control Center</h1>
            <p className="app-subtitle">
              {project ? `Monitoring ${project.name}` : "Select a project to start a conversation."}
            </p>
          </div>
          <div className="app-actions">
            <button
              type="button"
              className="app-primary-button"
              onClick={handleCreateChat}
              disabled={!project?.id || creatingChat}
            >
              {creatingChat ? "Creating…" : "New Chat"}
            </button>
          </div>
        </header>
        {error ? <div className="app-error">{error}</div> : null}
        <main className="app-content">{renderContent()}</main>
      </div>
    </div>
  );
}
