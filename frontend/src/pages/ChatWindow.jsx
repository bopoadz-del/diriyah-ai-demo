import React from "react";

const sampleMessages = [
  { id: 1, sender: "System", text: "Welcome to the Diriyah AI assistant." },
  { id: 2, sender: "Analyst", text: "Share the latest progress for Project Falcon." },
  { id: 3, sender: "Assistant", text: "Structural review is on track and BOQ alignment is green." },
];

export default function ChatWindow() {
  return (
    <div className="flex h-full flex-col bg-white">
      <header className="border-b px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Project Chat</h1>
        <p className="text-sm text-gray-500">Collaborate with your delivery teams in real time.</p>
      </header>
      <main className="flex-1 space-y-4 overflow-auto px-6 py-4">
        {sampleMessages.map((message) => (
          <div key={message.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="text-xs uppercase tracking-wide text-gray-500">{message.sender}</p>
            <p className="text-sm text-gray-700">{message.text}</p>
          </div>
        ))}
      </main>
      <footer className="border-t bg-gray-50 px-6 py-4">
        <div className="flex items-center gap-3">
          <input
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            placeholder="Type a message to your project team"
            readOnly
          />
          <button
            type="button"
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm"
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}
