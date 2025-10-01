import { useEffect, useMemo, useState } from "react";

import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import "./App.css";

const HEALTH_POLL_INTERVAL = 60_000;

export default function App() {
  const [user, setUser] = useState(null);
  const [project, setProject] = useState(null);
  const [projectDetails, setProjectDetails] = useState(null);
  const [selectedChat, setSelectedChat] = useState(null);
  const [view, setView] = useState("chat");
  const [health, setHealth] = useState({ status: "loading" });
  const [isFetchingProject, setIsFetchingProject] = useState(false);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const res = await fetch("/api/users/me");
        if (!res.ok) throw new Error(`users/me failed: ${res.status}`);
        setUser(await res.json());
      } catch (error) {
        console.warn("Failed to load user stub", error);
        setUser(null);
      }
    };
    loadUser();
  }, []);

  useEffect(() => {
    let timer;

    const loadHealth = async () => {
      try {
        const res = await fetch("/health");
        if (!res.ok) throw new Error(`health failed: ${res.status}`);
        setHealth(await res.json());
      } catch (error) {
        console.warn("Failed to fetch health payload", error);
        setHealth({ status: "error", message: "Backend unreachable" });
      } finally {
        timer = window.setTimeout(loadHealth, HEALTH_POLL_INTERVAL);
      }
    };

    loadHealth();
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!project?.id) {
      setProjectDetails(null);
      return;
    }

    let cancelled = false;
    const loadProject = async () => {
      setIsFetchingProject(true);
      try {
        const res = await fetch(`/api/projects/${project.id}`);
        if (!res.ok) throw new Error(`Project ${project.id} failed: ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setProjectDetails(data.project ?? data);
        }
      } catch (error) {
        console.warn("Failed to load project details", error);
        if (!cancelled) {
          setProjectDetails(project);
        }
      } finally {
        if (!cancelled) {
          setIsFetchingProject(false);
        }
      }
    };

    loadProject();
    return () => {
      cancelled = true;
    };
  }, [project]);

  const activeProject = useMemo(() => projectDetails ?? project, [project, projectDetails]);

  return (
    <div className="app-shell">
      <Sidebar
        project={activeProject}
        selectedChat={selectedChat}
        setProject={(nextProject) => {
          setProject(nextProject);
          setSelectedChat(null);
        }}
        setSelectedChat={setSelectedChat}
        setView={setView}
      />
      <div className="app-main">
        <Navbar
          user={user}
          project={activeProject}
          health={health}
          loadingProject={isFetchingProject}
        />
        <ChatWindow
          project={activeProject}
          selectedChat={selectedChat}
          view={view}
          setView={setView}
          user={user}
        />
      </div>
    </div>
  );
}
