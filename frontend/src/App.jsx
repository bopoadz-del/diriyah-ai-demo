import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ChatWindow from "./components/ChatWindow";
import AlertsPanel from "./components/AlertsPanel";
import ProjectDashboard from "./components/ProjectDashboard";

function App() {
  return (
    <Router>
      <div className="flex h-screen">
        <div className="flex-1 border-r">
          <Routes>
            <Route path="/" element={<ChatWindow />} />
            <Route path="/projects/:id" element={<ProjectDashboard />} />
          </Routes>
        </div>
        <div className="w-96">
          <AlertsPanel />
        </div>
      </div>
    </Router>
  );
}

export default App;
