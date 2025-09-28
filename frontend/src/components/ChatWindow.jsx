import React, { useState, useRef } from "react";
const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const fileInputRef = useRef(null);
  const handleSend = async (msg) => {
    if (!msg.trim()) return;
    const response = await fetch("/api/chat", { method: "POST", body: new URLSearchParams({ message: msg }) });
    const data = await response.json();
    setMessages((prev) => [...prev, { user: msg, bot: data.response }]);
    setInput("");
  };
  const handleMicClick = async () => {
    if (!navigator.mediaDevices || !window.MediaRecorder) { alert("Audio recording not supported."); return; }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream);
    const chunks = [];
    mr.ondataavailable = (e) => chunks.push(e.data);
    mr.onstop = async () => {
      const blob = new Blob(chunks, { type: "audio/wav" });
      const formData = new FormData();
      formData.append("audio", blob, "recording.wav");
      const res = await fetch("/api/speech-to-text", { method: "POST", body: formData });
      const data = await res.json();
      setMessages((prev) => [...prev, { user: "[Mic Input]", bot: data.text }]);
    };
    mr.start(); setTimeout(() => mr.stop(), 5000);
  };
  const handleCameraClick = () => fileInputRef.current.click();
  const handleImageChange = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    const formData = new FormData(); formData.append("image", file);
    const res = await fetch("/api/vision", { method: "POST", body: formData });
    const data = await res.json();
    setMessages((prev) => [...prev, { user: "[Image Uploaded]", bot: `Detections: ${JSON.stringify(data.detections)}` }]);
  };
  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((msg, i) => (<div key={i}><p><strong>You:</strong> {msg.user}</p><p><strong>Bot:</strong> {msg.bot}</p></div>))}
      </div>
      <div className="input-bar">
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message..." />
        <button onClick={handleMicClick}>Mic</button>
        <button onClick={handleCameraClick}>Camera</button>
        <input type="file" accept="image/*" capture="environment" style={{ display: "none" }} ref={fileInputRef} onChange={handleImageChange} />
        <button onClick={() => handleSend(input)}>Send</button>
      </div>
    </div>
  );
};
export default ChatWindow;
