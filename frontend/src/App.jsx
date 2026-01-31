import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import ChatUI from "./components/ChatUI";
import HydrationDashboard from "./components/hydration/HydrationDashboard";
import { PDPProvider } from "./contexts/PDPContext";
import { apiFetch } from "./lib/api";
import "./App.css";

function HydrationRoute() {
  const { workspaceId } = useParams();
  return <HydrationDashboard workspaceId={workspaceId} />;
}

function MainShell() {
  const { t } = useTranslation();
  const [workspace, setWorkspace] = useState({ projects: [], chatGroups: [], conversations: {} });
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [activeChatId, setActiveChatId] = useState(null);
  const [microphoneEnabled, setMicrophoneEnabled] = useState(false);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const synchroniseShell = useCallback((data) => {
    setWorkspace({
      projects: data.projects ?? [],
      chatGroups: data.chatGroups ?? [],
      conversations: data.conversations ?? {},
    });
    setActiveProjectId(data.activeProjectId ?? null);
    setActiveChatId(data.activeChatId ?? null);
    setMicrophoneEnabled(Boolean(data.microphoneEnabled));
  }, []);

  const applyConversationUpdate = useCallback((data) => {
    setWorkspace((previous) => ({
      projects: previous.projects,
      chatGroups: data.chatGroups ?? previous.chatGroups,
      conversations: {
        ...previous.conversations,
        [data.conversation.id]: data.conversation,
      },
    }));
    setActiveChatId(data.conversation.id);
  }, []);

  const loadWorkspace = useCallback(async () => {
    try {
      const response = await apiFetch("/api/workspace/shell");
      if (!response.ok) {
        throw new Error(`Failed to load workspace: ${response.status}`);
      }
      const data = await response.json();
      synchroniseShell(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [synchroniseShell]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  const activeProject = useMemo(
    () => workspace.projects.find((project) => project.id === activeProjectId) ?? null,
    [workspace.projects, activeProjectId],
  );

  const activeConversation = useMemo(
    () => (activeChatId ? workspace.conversations[activeChatId] : undefined),
    [workspace.conversations, activeChatId],
  );

  const handleProjectChange = async (projectId) => {
    setError(null);
    setActiveProjectId(projectId);
    try {
      const response = await apiFetch("/api/workspace/active-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId }),
      });
      if (!response.ok) {
        throw new Error("Unable to update active project");
      }
      const data = await response.json();
      synchroniseShell(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleChatSelect = async (chatId) => {
    setError(null);
    setActiveChatId(chatId);
    try {
      const response = await apiFetch(`/api/workspace/chats/${chatId}/read`, { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to open conversation");
      }
      const data = await response.json();
      applyConversationUpdate(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCreateChat = async () => {
    if (!activeProjectId) return;
    setError(null);
    try {
      const response = await apiFetch("/api/workspace/chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId: activeProjectId }),
      });
      if (!response.ok) {
        throw new Error("Unable to create conversation");
      }
      const data = await response.json();
      applyConversationUpdate(data);
      setIsContextPanelOpen(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMessageSubmit = async (chatId, body) => {
    setError(null);
    try {
      const response = await apiFetch(`/api/workspace/chats/${chatId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body, projectId: activeProjectId }),
      });
      if (!response.ok) {
        throw new Error("Unable to submit message");
      }
      const data = await response.json();
      applyConversationUpdate(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAttachmentUpload = async (chatId, fileName) => {
    setError(null);
    try {
      const response = await apiFetch(`/api/workspace/chats/${chatId}/attachments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileName }),
      });
      if (!response.ok) {
        throw new Error("Unable to register attachment");
      }
      const conversation = await response.json();
      setWorkspace((previous) => ({
        projects: previous.projects,
        chatGroups: previous.chatGroups,
        conversations: { ...previous.conversations, [conversation.id]: conversation },
      }));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMicrophoneToggle = async () => {
    setError(null);
    try {
      const response = await apiFetch("/api/workspace/microphone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !microphoneEnabled }),
      });
      if (!response.ok) {
        throw new Error("Unable to update microphone state");
      }
      const data = await response.json();
      setMicrophoneEnabled(Boolean(data.enabled));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMessageAction = async (chatId, messageId, action) => {
    setError(null);
    try {
      const response = await apiFetch(`/api/workspace/messages/${messageId}/action`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) {
        throw new Error("Unable to record message action");
      }
      await handleChatSelect(chatId);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleContextPanel = () => {
    setIsContextPanelOpen((current) => !current);
  };

  return (
    <PDPProvider>
      <div className="app">
        <Sidebar
          projects={workspace.projects}
          chatGroups={workspace.chatGroups}
          activeProjectId={activeProjectId}
          activeChatId={activeChatId}
          onProjectChange={handleProjectChange}
          onChatSelect={handleChatSelect}
          onCreateChat={handleCreateChat}
          loading={loading}
          error={error}
          t={t}
        />
        <ChatUI
          activeProject={activeProject}
          activeConversation={activeConversation}
          onMessageSubmit={handleMessageSubmit}
          onAttachmentUpload={handleAttachmentUpload}
          onMessageAction={handleMessageAction}
          microphoneEnabled={microphoneEnabled}
          onMicrophoneToggle={handleMicrophoneToggle}
          isContextPanelOpen={isContextPanelOpen}
          onToggleContextPanel={handleToggleContextPanel}
          t={t}
        />
      </div>
    </PDPProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainShell />} />
        <Route path="/hydration/:workspaceId" element={<HydrationRoute />} />
      </Routes>
    </BrowserRouter>
  );
}
