import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Sidebar from "./components/Sidebar";
import ChatUI from "./components/ChatUI";
import { PDPProvider } from "./contexts/PDPContext";
import "./App.css";

function App() {
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
      const response = await fetch("/api/workspace/shell");
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
      const response = await fetch("/api/workspace/active-project", {
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
      const response = await fetch(`/api/workspace/chats/${chatId}/read`, { method: "POST" });
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
      const response = await fetch("/api/workspace/chats", {
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
      const response = await fetch(`/api/workspace/chats/${chatId}/messages`, {
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
      const response = await fetch(`/api/workspace/chats/${chatId}/attachments`, {
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
      const response = await fetch("/api/workspace/microphone", {
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
      const response = await fetch(`/api/workspace/messages/${messageId}/action`, {
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

  if (loading) {
    return <div className="app-shell app-shell--loading">{t("app.loading")}</div>;
  }

  if (error) {
    return (
      <div className="app-shell app-shell--error" role="alert">
        {error}
      </div>
    );
  }

  if (!activeProject || !activeConversation) {
    return (
      <div className="app-shell app-shell--error" role="alert">
        {t("app.unavailable")}
      </div>
    );
  }

  return (
    <PDPProvider userId={1} projectId={activeProjectId}>
      <div className={`app-shell ${isContextPanelOpen ? "app-shell--panel-open" : ""}`}>
        <Sidebar
          projects={workspace.projects}
          activeProjectId={activeProjectId}
          onProjectChange={handleProjectChange}
          chatGroups={workspace.chatGroups}
          activeChatId={activeChatId}
          onChatSelect={handleChatSelect}
          onCreateChat={handleCreateChat}
        />
        <ChatUI
          project={activeProject}
          conversation={activeConversation}
          isContextPanelOpen={isContextPanelOpen}
          onToggleContextPanel={handleToggleContextPanel}
          onSubmitMessage={handleMessageSubmit}
          onUploadAttachment={handleAttachmentUpload}
          onToggleMicrophone={handleMicrophoneToggle}
          microphoneEnabled={microphoneEnabled}
          onMessageAction={handleMessageAction}
        />
      </div>
    </PDPProvider>
  );
}

export default App;
