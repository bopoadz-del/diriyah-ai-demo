import { useEffect, useMemo, useState } from "react";
import MessageActions from "./MessageActions";
import UploadButton from "./UploadButton";
import MicButton from "./MicButton";
import CamButton from "./CamButton";

function makeMessage(role, content, offsetMs = 0) {
  return {
    id: `${role}-${Math.random().toString(36).slice(2, 10)}-${Date.now()}`,
    role,
    content,
    created_at: new Date(Date.now() - offsetMs).toISOString(),
    read: role !== "user",
  };
}

function buildFixtureMessages(project, chat) {
  const title = project?.name || "the active project";
  return [
    makeMessage(
      "assistant",
      `👋 Welcome back! I'm monitoring ${title}. Ask anything about progress, risks, or Drive documents.`,
      1000 * 60 * 60,
    ),
    makeMessage(
      "user",
      `Give me a progress pulse for ${title}.`,
      1000 * 50,
    ),
    makeMessage(
      "assistant",
      `${title} is tracking at ${project?.progress_percent ?? "around"}%. Next milestone: ${
        project?.next_milestone || "design review"
      }.`,
      1000 * 45,
    ),
    makeMessage(
      "user",
      "Any blockers I should be aware of?",
      1000 * 20,
    ),
    makeMessage(
      "assistant",
      "No critical blockers logged this week. Two RFIs pending consultant feedback.",
      1000 * 15,
    ),
  ].map((message) => ({ ...message, chat_id: chat }));
}

function craftAssistantReply(prompt, project) {
  const title = project?.name || "the project";
  if (!prompt) return `Here's the latest for ${title}.`;
  const lower = prompt.toLowerCase();
  if (lower.includes("risk")) {
    return `Risk outlook for ${title}: no high severity issues. Watch cost variance on façade packages.`;
  }
  if (lower.includes("schedule") || lower.includes("timeline")) {
    return `${title} remains on track. Current progress is ${project?.progress_percent ?? 65}% with the next milestone at ${
      project?.next_milestone || "the upcoming design review"
    }.`;
  }
  if (lower.includes("document")) {
    return `The latest documents for ${title} were synced 3 hours ago. Check the Drive QA folder for fresh uploads.`;
  }
  return `Here's a contextual update on ${title}: site works steady, coordination meetings scheduled tomorrow, and AI summaries available in analytics.`;
}

export default function Chat({ project, chat }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!chat) {
      setMessages([]);
      setStatus("Select a chat from the sidebar to start a conversation.");
      return;
    }
    setMessages(buildFixtureMessages(project, chat));
    setStatus("Showing fixture conversation – ready for Render debugging.");
  }, [chat, project]);

  const send = () => {
    const trimmed = input.trim();
    if (!project?.id || !chat || !trimmed) return;
    const userMessage = makeMessage("user", trimmed);
    const reply = makeMessage("assistant", craftAssistantReply(trimmed, project));
    setMessages((prev) => [...prev, userMessage, reply]);
    setInput("");
  };

  const summarizeChat = () => {
    if (!chat) return;
    const important = messages.filter((message) => message.role === "assistant").slice(-3);
    const summary = important.length
      ? important.map((message) => `• ${message.content}`).join("\n")
      : "No assistant messages yet";
    setMessages((prev) => [
      ...prev,
      makeMessage("assistant", `Summary for ${project?.name || "this chat"}:\n${summary}`),
    ]);
  };

  const handleRefresh = (messageId, messageIndex) => {
    const target = messages[messageIndex];
    if (!target || target.role !== "assistant") return;
    const lastUserPrompt = [...messages]
      .slice(0, messageIndex)
      .reverse()
      .find((message) => message.role === "user")?.content;
    const refreshed = makeMessage("assistant", craftAssistantReply(lastUserPrompt || "update", project));
    setMessages((prev) => prev.map((message) => (message.id === messageId ? refreshed : message)));
  };

  const headerTitle = useMemo(() => {
    if (!project) return "No project selected";
    return `${project.name} · ${project.location || "Location TBC"}`;
  }, [project]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-white/80">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">{headerTitle}</p>
          <h3 className="text-lg font-semibold text-slate-900">Chat thread {chat || "—"}</h3>
          {status && <p className="text-xs text-slate-500 mt-1">{status}</p>}
        </div>
        <button
          className="rounded-full border border-slate-200 px-4 py-1.5 text-sm hover:bg-slate-50"
          onClick={summarizeChat}
        >
          🧠 Summarise chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 bg-gradient-to-b from-white/60 to-white">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex items-start gap-3 rounded-xl border border-slate-100 bg-white/80 px-4 py-3 shadow-sm ${
              message.role === "assistant" ? "" : "border-slate-200"
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800">
                  {message.role === "assistant" ? "Diriyah Brain" : "You"}
                </span>
                <span className="text-xs text-slate-400">
                  {message.created_at ? new Date(message.created_at).toLocaleString() : ""}
                </span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-slate-700 whitespace-pre-line">{message.content}</p>
            </div>
            <MessageActions msg={message} index={index} onRefresh={() => handleRefresh(message.id, index)} />
          </div>
        ))}
        {!messages.length && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white/70 px-4 py-6 text-center text-sm text-slate-500">
            Start the conversation by sending a message.
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white/90 px-6 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <input
            className="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={project ? `Ask about ${project.name}` : "Pick a project to start chatting"}
          />
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-slate-700"
              onClick={send}
            >
              Send
            </button>
            <UploadButton projectId={project?.id} driveFolderId={project?.drive_id} chatId={chat} />
            <MicButton projectId={project?.id} />
            <CamButton projectId={project?.id} />
          </div>
        </div>
      </div>
    </div>
  );
}
