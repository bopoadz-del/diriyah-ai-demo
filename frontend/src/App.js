import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import AlertsPanel from "./components/AlertsPanel";
import Analytics from "./components/Analytics";
import ChatWindow from "./components/ChatWindow";
import Navbar from "./components/Navbar";
import ProjectDashboard from "./components/ProjectDashboard";
import Settings from "./components/Settings";
import Sidebar from "./components/Sidebar";
import SplitLayout from "./components/SplitLayout";

const App = () => {
  const handleSelectProject = (projectId, projectName) => {
    // eslint-disable-next-line no-console
    console.log("Project selected:", projectId ?? projectName);
  };

  return (
    <Router>
      <div className="app-container">
        <Navbar />
        <div className="content">
          <Sidebar onSelectProject={handleSelectProject} />
          <main className="main-view">
            <Routes>
              <Route path="/" element={<ChatWindow />} />
              <Route path="/projects/:id" element={<ProjectDashboard />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/split" element={<SplitLayout />} />
            </Routes>
          </main>
          <aside className="alerts-view">
            <AlertsPanel />
          </aside>
        </div>
      </div>
    </Router>
  );
};

export default App;
