import React, { useCallback, useEffect, useRef, useState } from "react";

const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);
  const recordingTimeoutRef = useRef(null);

  useEffect(() => {
    return () => {
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
    };
  }, []);

  const appendMessage = useCallback((message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const sendMessage = useCallback(
    async (message) => {
      const trimmed = message.trim();
      if (!trimmed) {
        return;
      }

      setIsSending(true);
      setError("");
      appendMessage({ role: "user", content: trimmed });
      setInput("");

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          body: new URLSearchParams({ message: trimmed }),
        });

        if (!response.ok) {
          throw new Error(`Chat request failed (${response.status})`);
        }

        const data = await response.json();
        appendMessage({ role: "bot", content: data.response ?? "" });
      } catch (requestError) {
        console.error("Chat request failed", requestError);
        setError("Unable to send message. Please try again.");
        appendMessage({
          role: "bot",
          content: "I ran into an issue processing that message.",
        });
      } finally {
        setIsSending(false);
      }
    },
    [appendMessage],
  );

  const handleSendClick = useCallback(() => {
    void sendMessage(input);
  }, [input, sendMessage]);

  const handleMicClick = useCallback(async () => {
    if (!navigator.mediaDevices || typeof window.MediaRecorder === "undefined") {
      window.alert("Audio recording is not supported in this browser.");
      return;
    }

    try {
      setError("");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        clearTimeout(recordingTimeoutRef.current);
        stream.getTracks().forEach((track) => track.stop());

        try {
          const audioBlob = new Blob(chunks, { type: "audio/wav" });
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.wav");

          const response = await fetch("/api/speech-to-text", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`Speech-to-text failed (${response.status})`);
          }

          const data = await response.json();
          appendMessage({ role: "user", content: "[Mic Input]" });
          appendMessage({ role: "bot", content: data.text ?? "" });
        } catch (speechError) {
          console.error("Speech-to-text failed", speechError);
          setError("Unable to process the audio clip.");
        }
      };

      recorder.start();
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      recordingTimeoutRef.current = window.setTimeout(() => {
        recorder.stop();
      }, 5000);
    } catch (micError) {
      console.error("Microphone access denied", micError);
      setError("Microphone access is required to record audio.");
    }
  }, [appendMessage]);

  const handleCameraClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleImageChange = useCallback(
    async (event) => {
      const file = event.target.files?.[0];
      if (!file) {
        return;
      }

      setError("");
      try {
        const formData = new FormData();
        formData.append("image", file);

        const response = await fetch("/api/vision", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Vision request failed (${response.status})`);
        }

        const data = await response.json();
        appendMessage({ role: "user", content: "[Image Uploaded]" });
        appendMessage({
          role: "bot",
          content: `Detections: ${JSON.stringify(data.detections ?? [])}`,
        });
      } catch (visionError) {
        console.error("Vision request failed", visionError);
        setError("Unable to analyse the image.");
      } finally {
        event.target.value = "";
      }
    },
    [appendMessage],
  );

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`message message-${message.role}`}>
            <p>
              <strong>{message.role === "bot" ? "Diriyah Brain:" : "You:"}</strong>
              {" "}
              {message.content}
            </p>
          </div>
        ))}
      </div>

      <div className="input-bar">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Type a message..."
          disabled={isSending}
        />
        <button type="button" onClick={handleMicClick}>
          Mic
        </button>
        <button type="button" onClick={handleCameraClick}>
          Camera
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={handleImageChange}
        />
        <button type="button" onClick={handleSendClick} disabled={isSending}>
          {isSending ? "Sending…" : "Send"}
        </button>
      </div>

      {error && <p className="chat-error">{error}</p>}
    </div>
  );
};

export default ChatWindow;
