import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Chat from "./components/Chat";
import Admin from "./pages/Admin";
import Metrics from "./pages/Metrics";
import ProjectSettings from "./pages/ProjectSettings";

export default function App() {
  const [project, setProject] = useState(null);
  const [selectedChat, setSelectedChat] = useState(null);
  const [view, setView] = useState("chat");

  return (
    <div className="flex h-screen">
      <Sidebar
        project={project}
        setProject={setProject}
        setSelectedChat={setSelectedChat}
        setView={setView}
      />
      <div className="flex-1">
        {view === "chat" && <Chat project={project} chat={selectedChat} />}
        {view === "admin" && <Admin />}
        {view === "metrics" && <Metrics />}
        {view === "settings" && <ProjectSettings projectId={project?.id || null} />}
      </div>
    </div>
  );
}