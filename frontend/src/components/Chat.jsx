import React, { useMemo, useState } from "react";

const seedMessages = [
  {
    id: "1",
    role: "ai",
    content: "Welcome back! Let me know how I can support the site team today.",
    timestamp: "09:41",
  },
  {
    id: "2",
    role: "user",
    content: "Summarise the open actions for Villa 100.",
    timestamp: "09:42",
  },
  {
    id: "3",
    role: "ai",
    content: "Villa 100 has three open actions: podium slab pour pending procurement sign-off, façade mock-up review on Thursday, and workforce ramp-up awaiting HR.",
    timestamp: "09:44",
  },
];

export default function Chat({ project }) {
  const [input, setInput] = useState("");
  const messages = useMemo(() => seedMessages, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    setInput("");
  };

  return (
    <section className="flex h-full flex-col">
      <div className="mx-auto w-full max-w-4xl flex-1 overflow-auto px-6 py-8">
        <p className="mb-6 text-sm text-gray-500">Conversation for <span className="font-semibold text-gray-700">{project}</span></p>
        <div className="space-y-4">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`max-w-xl rounded-2xl border px-4 py-3 shadow-sm ${
                message.role === "user" ? "ml-auto border-[#a67c52] bg-[#f6efe6]" : "border-gray-200 bg-white"
              }`}
            >
              <header className="mb-1 flex items-center justify-between text-xs text-gray-400">
                <span className="font-medium text-gray-600">{message.role === "user" ? "You" : "Diriyah AI"}</span>
                <span>{message.timestamp}</span>
              </header>
              <p className="text-sm text-gray-700">{message.content}</p>
            </article>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white/90 px-6 py-4 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-4xl items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-full border border-gray-300 bg-white px-4 py-3 text-sm shadow-sm focus:border-[#a67c52] focus:outline-none"
          />
          <button
            type="submit"
            disabled
            className="rounded-full bg-[#a67c52] px-5 py-3 text-sm font-semibold text-white opacity-60"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
