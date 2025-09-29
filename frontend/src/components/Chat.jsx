import { useEffect, useState } from "react";
import MessageActions from "./MessageActions";
import UploadButton from "./UploadButton";
import MicButton from "./MicButton";
import CamButton from "./CamButton";

export default function Chat({ project, chat }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const reload = async () => {
    if (chat) {
      const r = await fetch(`/api/chats/${chat}/messages`);
      setMessages(await r.json());
    }
  };

  useEffect(() => { reload(); }, [chat]);

  const send = async () => {
    if (!project?.id || !chat || !input.trim()) return;

    const res = await fetch(`/api/chats/${chat}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "user", content: input }),
    });
    const userMsg = await res.json();

    const aiRes = await fetch(`/api/ai/query`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: String(project.id), query: input }),
    });
    const aiData = await aiRes.json();

    const res2 = await fetch(`/api/chats/${chat}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "assistant", content: aiData.answer }),
    });
    const aiMsg = await res2.json();

    setMessages(prev => [...prev, userMsg, aiMsg]);
    setInput("");
  };

  const summarizeChat = async () => {
    if (!chat) return;
    const res = await fetch(`/api/ai/summarize`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ chat_id: chat })
    });
    const data = await res.json();
    const res2 = await fetch(`/api/chats/${chat}/messages`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ role: "assistant", content: data.summary })
    });
    const msg = await res2.json();
    setMessages(prev => [...prev, msg]);
  };

  const handleRefresh = async (msgId, msgIndex) => {
    const msg = messages[msgIndex];
    if (msg.role !== "assistant") return;

    let prompt = "";
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].role === "user") { prompt = messages[i].content; break; }
    }
    if (!prompt) return;

    const aiRes = await fetch(`/api/ai/query`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: String(project.id), query: prompt }),
    });
    const aiData = await aiRes.json();

    await fetch(`/api/messages/${msgId}?content=${encodeURIComponent(aiData.answer)}`, { method: "PUT" });
    await reload();
  };

  return (
    <div className="p-4 flex flex-col h-full">
      <div className="flex justify-between items-center mb-2">
        <div className="text-sm text-gray-600">Project: {project?.name || "—"} · Chat #{chat || "—"}</div>
        <button className="border px-2 py-1 rounded" onClick={summarizeChat}>🧠 Summarize Chat</button>
      </div>

      <div className="flex-1 overflow-auto border rounded p-2">
        {messages.map((m, i) => (
          <div key={m.id} className="flex justify-between hover:bg-gray-50 p-1 rounded">
            <div className="pr-2">
              <div><b>{m.role}:</b> {m.content}</div>
              <div className="text-xs text-gray-500">
                {m.created_at ? new Date(m.created_at).toLocaleString() : ""} {m.read ? "· Read" : ""}
              </div>
            </div>
            <MessageActions msg={m} index={i} onRefresh={() => handleRefresh(m.id, i)} />
          </div>
        ))}
      </div>

      <div className="flex mt-2 gap-2">
        <input className="flex-1 border p-2" value={input} onChange={e => setInput(e.target.value)} placeholder="Type a message…" />
        <button className="px-3 py-2 border" onClick={send}>Send</button>
        <UploadButton projectId={project?.id} driveFolderId={project?.drive_id} chatId={chat} />
        <MicButton projectId={project?.id} />
        <CamButton projectId={project?.id} />
      </div>
    </div>
  );
}