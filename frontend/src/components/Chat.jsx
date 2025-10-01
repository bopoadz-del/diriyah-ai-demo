import { useEffect, useMemo, useRef, useState } from "react";
import MessageActions from "./MessageActions";
import UploadButton from "./UploadButton";
import MicButton from "./MicButton";
import CamButton from "./CamButton";

const formatTimestamp = value => {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value);
  }
};

export default function Chat({ project, chat }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  const canSend = Boolean(project?.id && chat && input.trim());

  const reload = async signal => {
    if (!chat) {
      setMessages([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/chats/${chat}/messages`, { signal });
      if (!response.ok) {
        throw new Error(`Failed to load messages: ${response.status}`);
      }
      const data = await response.json();
      setMessages(Array.isArray(data) ? data : []);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Unable to fetch messages", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    reload(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat]);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const appendMessage = update => {
    setMessages(prev => [...prev, ...(Array.isArray(update) ? update : [update])]);
  };

  const send = async () => {
    if (!canSend) return;

    const content = input.trim();
    setInput("");
    setError(null);

    try {
      const userRes = await fetch(`/api/chats/${chat}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "user", content }),
      });
      if (!userRes.ok) {
        throw new Error(`Failed to send message: ${userRes.status}`);
      }
      const userMsg = await userRes.json();
      appendMessage(userMsg);

      const aiRes = await fetch(`/api/ai/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: String(project.id), query: content }),
      });
      if (!aiRes.ok) {
        throw new Error(`AI query failed: ${aiRes.status}`);
      }
      const aiData = await aiRes.json();
      const answer = aiData?.answer ?? "No answer provided.";

      const assistantRes = await fetch(`/api/chats/${chat}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "assistant", content: answer }),
      });
      if (!assistantRes.ok) {
        throw new Error(`Failed to save assistant reply: ${assistantRes.status}`);
      }
      const assistantMsg = await assistantRes.json();
      appendMessage(assistantMsg);
    } catch (err) {
      console.error("Unable to send message", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      reload();
    }
  };

  const summarizeChat = async () => {
    if (!chat) return;
    setError(null);
    try {
      const res = await fetch(`/api/ai/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chat }),
      });
      if (!res.ok) {
        throw new Error(`Failed to summarize chat: ${res.status}`);
      }
      const data = await res.json();
      const summary = data?.summary ?? "No summary returned.";

      const save = await fetch(`/api/chats/${chat}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "assistant", content: summary }),
      });
      if (!save.ok) {
        throw new Error(`Failed to store summary: ${save.status}`);
      }
      const savedMsg = await save.json();
      appendMessage(savedMsg);
    } catch (err) {
      console.error("Unable to summarize chat", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const handleRefresh = async (msgId, msgIndex) => {
    const msg = messages[msgIndex];
    if (!msg || msg.role !== "assistant" || !project?.id) return;

    let prompt = "";
    for (let i = msgIndex - 1; i >= 0; i -= 1) {
      const candidate = messages[i];
      if (candidate?.role === "user") {
        prompt = candidate.content;
        break;
      }
    }
    if (!prompt) return;

    try {
      const aiRes = await fetch(`/api/ai/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: String(project.id), query: prompt }),
      });
      if (!aiRes.ok) {
        throw new Error(`AI refresh failed: ${aiRes.status}`);
      }
      const aiData = await aiRes.json();
      const content = aiData?.answer ?? msg.content;

      const update = await fetch(
        `/api/messages/${msgId}?content=${encodeURIComponent(content)}`,
        { method: "PUT" },
      );
      if (!update.ok) {
        throw new Error(`Failed to update message: ${update.status}`);
      }
      await reload();
    } catch (err) {
      console.error("Unable to refresh message", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  const emptyState = useMemo(() => {
    if (loading) return "Loading messages…";
    if (!project?.id) return "Select a project to begin chatting.";
    if (!chat) return "Choose a chat session from the sidebar.";
    return "No messages yet. Start the conversation below.";
  }, [chat, loading, project?.id]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b pb-3">
        <div className="text-sm text-gray-600">
          Project: {project?.name || "—"} · Chat #{chat || "—"}
        </div>
        <button
          type="button"
          className="rounded border px-2 py-1 text-sm hover:bg-gray-50"
          onClick={summarizeChat}
          disabled={!chat}
        >
          🧠 Summarize Chat
        </button>
      </div>

      <div ref={scrollRef} className="mt-3 flex-1 overflow-auto rounded border bg-white p-3 shadow-inner">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            {emptyState}
          </div>
        ) : (
          <ul className="space-y-3">
            {messages.map((m, i) => (
              <li key={m.id || `${m.role}-${i}`} className="rounded border border-gray-200 p-2 hover:border-gray-300">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="text-sm font-semibold capitalize text-slate-700">{m.role}</div>
                    <div className="whitespace-pre-wrap text-sm text-slate-900">{m.content}</div>
                    <div className="mt-1 text-xs text-gray-500">
                      {formatTimestamp(m.created_at)} {m.read ? "· Read" : ""}
                    </div>
                  </div>
                  <MessageActions msg={m} index={i} onRefresh={() => handleRefresh(m.id, i)} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error ? (
        <div className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          className="flex-1 rounded border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={project?.id ? "Type a message…" : "Select a project to enable chat"}
          disabled={!project?.id || !chat}
          onKeyDown={event => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send();
            }
          }}
        />
        <button
          type="button"
          className="rounded border bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300"
          onClick={send}
          disabled={!canSend}
        >
          Send
        </button>
        <UploadButton projectId={project?.id} driveFolderId={project?.drive_id} chatId={chat} />
        <MicButton projectId={project?.id} />
        <CamButton projectId={project?.id} />
      </div>
    </div>
  );
}
