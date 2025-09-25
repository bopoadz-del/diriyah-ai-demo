import React, { useState } from 'react';
import axios from 'axios';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [file, setFile] = useState(null);

  const sendMessage = async () => {
    if (!input && !file) return;

    const formData = new FormData();
    formData.append("message", input);
    if (file) {
      formData.append("file", file);
    }

    try {
      const res = await axios.post("/api/chat", formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessages([...messages, { role: "user", text: input, file: file?.name }, { role: "ai", data: res.data.result }]);
    } catch (err) {
      console.error(err);
      setMessages([...messages, { role: "ai", text: "Error: could not process" }]);
    }

    setInput("");
    setFile(null);
  };

  const renderAIResponse = (data) => {
    if (!data) return null;

    if (Array.isArray(data)) {
      const keys = Object.keys(data[0] || {});
      return (
        <table className="table-auto border-collapse border border-gray-400 text-sm w-full">
          <thead>
            <tr>
              {keys.map((k) => (
                <th key={k} className="border border-gray-400 px-2 py-1 bg-gray-100">{k}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                {keys.map((k) => (
                  <td key={k} className="border border-gray-400 px-2 py-1">{row[k]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (typeof data === "object") {
      return (
        <table className="table-auto border-collapse border border-gray-400 text-sm w-full">
          <tbody>
            {Object.entries(data).map(([k, v]) => (
              <tr key={k}>
                <td className="border border-gray-400 px-2 py-1 font-semibold bg-gray-100">{k}</td>
                <td className="border border-gray-400 px-2 py-1">{JSON.stringify(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    return <pre>{String(data)}</pre>;
  };

  return (
    <div className="chat-container p-4">
      <div className="messages mb-4 h-96 overflow-y-auto border p-2">
        {messages.map((m, i) => (
          <div key={i} className={`mb-4 ${m.role === "user" ? "text-right" : "text-left"}`}>
            <span className="block font-semibold">{m.role.toUpperCase()}:</span>
            {m.text && <p>{m.text}</p>}
            {m.file && <em className="block text-sm">📎 {m.file}</em>}
            {m.data && renderAIResponse(m.data)}
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message... (e.g. run cad takeoff, parse boq, check bim)"
          className="flex-1 border p-2"
        />
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          className="border p-2"
        />
        <button onClick={sendMessage} className="bg-blue-600 text-white px-4 py-2">Send</button>
      </div>
    </div>
  );
}

export default Chat;