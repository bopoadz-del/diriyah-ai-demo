import React, { useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Chat from "./components/Chat";
import Home from "./components/Home";
import Help from "./components/Help";
import Settings from "./components/Settings";
import "./styles/theme.css";
import "./styles/background.css";

function App() {
  const [activePage, setActivePage] = useState("home");
  const [activeProject, setActiveProject] = useState("Villa 100");

  const renderContent = () => {
    if (activePage === "home") {
      return <Home />;
    }
    if (activePage === "chat") {
      return <Chat project={activeProject} />;
    }
    if (activePage === "help") {
      return <Help />;
    }
    if (activePage === "settings") {
      return <Settings />;
    }
    return null;
  };

  return (
    <div className="chat-bg min-h-screen w-screen flex overflow-hidden">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        activeProject={activeProject}
        onSelect={setActiveProject}
      />
      <div className="flex-1 flex flex-col">
        <Header project={activeProject} activePage={activePage} />
        <main className="flex-1 overflow-auto bg-white/80 backdrop-blur-sm">{renderContent()}</main>
      </div>
    </div>
  );
}

export default App;
