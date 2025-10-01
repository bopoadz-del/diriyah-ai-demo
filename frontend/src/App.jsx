import { useMemo, useRef, useState } from "react";
import "./App.css";

const seededMessages = [
  {
    id: "m-1",
    role: "ai",
    content: "Welcome to Diriyah Brain AI. Select a project to begin reviewing today's activities.",
    timestamp: new Date("2024-09-18T09:41:00"),
  },
  {
    id: "m-2",
    role: "user",
    content: "Summarise the open structural actions for Villa 100.",
    timestamp: new Date("2024-09-18T09:43:00"),
  },
  {
    id: "m-3",
    role: "ai",
    content:
      "Villa 100 has three open actions: podium slab pour pending procurement sign-off, façade mock-up review scheduled Thursday, and workforce ramp-up approval awaiting HR.",
    timestamp: new Date("2024-09-18T09:44:00"),
  },
  {
    id: "m-4",
    role: "user",
    content: "Flag the procurement risk for the podium slab and notify the commercial lead.",
    timestamp: new Date("2024-09-17T17:21:00"),
  },
  {
    id: "m-5",
    role: "ai",
    content:
      "Risk flagged. Notification drafted to commercial lead with revised delivery timeline and escalation note.",
    timestamp: new Date("2024-09-17T17:22:00"),
  },
];

const chatGroups = [
  {
    id: "today",
    label: "Today",
    conversations: ["Villa 100 — Casting Delay", "Gateway Villas — Concrete Pour"],
  },
  {
    id: "week",
    label: "This Week",
    conversations: ["Downtown Tower — Procurement", "Cultural District — Logistics"],
  },
  {
    id: "archive",
    label: "Previous",
    conversations: ["Residences — Snag Review", "Retail Spine — Fit-Out"],
  },
];

const projects = ["Gateway Villas", "Downtown Towers", "Villa 100", "Cultural District"];

const formatDate = (date) =>
  new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(date);

const formatTime = (date) =>
  new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);

const IconSettings = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="icon__svg">
    <path
      d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8.5-3.5a6.82 6.82 0 0 0-.08-1l2.11-1.65-2-3.46-2.5.63a6.88 6.88 0 0 0-1.72-1l-.38-2.54H9.57l-.38 2.54a6.88 6.88 0 0 0-1.72 1l-2.5-.63-2 3.46 2.11 1.65a6.82 6.82 0 0 0 0 2l-2.11 1.65 2 3.46 2.5-.63a6.88 6.88 0 0 0 1.72 1l.38 2.54h4.74l.38-2.54a6.88 6.88 0 0 0 1.72-1l2.5.63 2-3.46-2.11-1.65a6.82 6.82 0 0 0 .08-1Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const IconFileText = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="icon__svg">
    <path
      d="M6 2.75h7.19a2 2 0 0 1 1.41.59l3.06 3.06a2 2 0 0 1 .59 1.41v12.44A1.75 1.75 0 0 1 16.5 22.25h-9A1.75 1.75 0 0 1 5.75 20.5V4.5A1.75 1.75 0 0 1 7.5 2.75"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M13.5 2.75V7h4.25"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M9 12.25h6M9 15.75h6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

const IconUser = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="icon__svg">
    <path
      d="M12 12.75a4.5 4.5 0 1 0-4.5-4.5 4.5 4.5 0 0 0 4.5 4.5Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M4.75 19.5a7.25 7.25 0 0 1 14.5 0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const IconUpload = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="icon__svg">
    <path
      d="M12 15.25V4.75M8.75 8.25 12 4.75l3.25 3.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M4.75 15.25v3.5a1.5 1.5 0 0 0 1.5 1.5h11.5a1.5 1.5 0 0 0 1.5-1.5v-3.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const IconCamera = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="icon__svg">
    <path
      d="M21.25 17.5a1.75 1.75 0 0 1-1.75 1.75H4.5A1.75 1.75 0 0 1 2.75 17.5v-8a1.75 1.75 0 0 1 1.75-1.75h2.12l1.2-1.94a1 1 0 0 1 .85-.46h4.36a1 1 0 0 1 .85.46l1.2 1.94h2.12a1.75 1.75 0 0 1 1.75 1.75Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M12 15.75a3 3 0 1 0-3-3 3 3 0 0 0 3 3Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const IconMic = ({ active }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={`icon__svg ${active ? "icon__svg--active" : ""}`}>
    <path
      d="M12 15.75a3.25 3.25 0 0 0 3.25-3.25V6.75A3.25 3.25 0 0 0 12 3.5a3.25 3.25 0 0 0-3.25 3.25v5.75A3.25 3.25 0 0 0 12 15.75Z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M5.75 11.5v1a6.25 6.25 0 0 0 12.5 0v-1M12 18.5v2.75"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

function App() {
  const [selectedProject, setSelectedProject] = useState(projects[0]);
  const [messages, setMessages] = useState(seededMessages);
  const [input, setInput] = useState("");
  const [collapsedGroups, setCollapsedGroups] = useState(() =>
    chatGroups.reduce((acc, group) => ({ ...acc, [group.id]: false }), {})
  );
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [micSupported, setMicSupported] = useState(true);
  const recognitionRef = useRef(null);
  const uploadInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const groupedMessages = useMemo(() => {
    const ordered = [...messages].sort((a, b) => a.timestamp - b.timestamp);
    const map = new Map();

    ordered.forEach((message) => {
      const key = formatDate(message.timestamp);
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key).push(message);
    });

    return Array.from(map.entries());
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim()) {
      return;
    }

    const entry = {
      id: `m-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, entry]);
    setInput("");
  };

  const toggleGroup = (id) => {
    setCollapsedGroups((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleContextPanel = () => {
    setIsPanelOpen((prev) => !prev);
  };

  const handleUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const message = {
      id: `m-${Date.now()}-upload`,
      role: "ai",
      content: `Indexed file: ${file.name} (metadata captured).`,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, message]);
    event.target.value = "";
  };

  const handleMicToggle = () => {
    if (typeof window === "undefined") {
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setMicSupported(false);
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = recognitionRef.current ?? new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0]?.transcript;
      if (transcript) {
        setInput((prev) => `${prev ? `${prev} ` : ""}${transcript}`.trimStart());
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  };

  const handleCameraCapture = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const message = {
      id: `m-${Date.now()}-camera`,
      role: "ai",
      content: `Image captured: ${file.name || "new photo"} (insights pending).`,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, message]);
    event.target.value = "";
  };

  const projectStatus = {
    tone: "connected",
    label: "Connected",
  };

  return (
    <div className={`app-shell ${isPanelOpen ? "app-shell--panel-open" : ""}`}>
      <aside className="sidebar" aria-label="Conversations sidebar">
        <div className="sidebar__logo">Diriyah Brain AI</div>

        <div className="sidebar__section">
          <label htmlFor="project-select" className="sidebar__label">
            Project workspace
          </label>
          <select
            id="project-select"
            className="sidebar__dropdown"
            value={selectedProject}
            onChange={(event) => setSelectedProject(event.target.value)}
          >
            {projects.map((project) => (
              <option key={project} value={project}>
                {project}
              </option>
            ))}
          </select>
        </div>

        <nav className="sidebar__section sidebar__chats" aria-label="Chat history">
          {chatGroups.map((group) => (
            <div key={group.id} className="sidebar__group">
              <button
                type="button"
                className="sidebar__group-toggle"
                onClick={() => toggleGroup(group.id)}
                aria-expanded={!collapsedGroups[group.id]}
              >
                <span>{group.label}</span>
                <span className="sidebar__group-caret" aria-hidden="true">
                  {collapsedGroups[group.id] ? "▸" : "▾"}
                </span>
              </button>
              <ul
                className={`sidebar__chat-list ${collapsedGroups[group.id] ? "sidebar__chat-list--collapsed" : ""}`}
              >
                {group.conversations.map((conversation) => (
                  <li key={conversation}>
                    <button type="button" className="sidebar__chat-button">
                      {conversation}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="sidebar__bottom" aria-label="Workspace settings">
          <button type="button" className="sidebar__icon" aria-label="Settings">
            <IconSettings />
          </button>
          <button type="button" className="sidebar__icon" aria-label="Documentation">
            <IconFileText />
          </button>
          <button type="button" className="sidebar__icon" aria-label="Profile">
            <IconUser />
          </button>
        </div>
      </aside>

      <main className="chat" aria-label="Chat panel">
        <header className="chat__header">
          <div className="chat__project">
            <div className="chat__project-name">{selectedProject}</div>
            <div className="chat__project-meta">Central delivery workspace</div>
          </div>
          <div className="chat__header-actions">
            <span className={`chat__status chat__status--${projectStatus.tone}`} aria-label={projectStatus.label} />
            <button type="button" className="chat__context-toggle" onClick={toggleContextPanel}>
              Context
            </button>
          </div>
        </header>

        <div className="chat__window" aria-live="polite">
          {groupedMessages.map(([dateLabel, items]) => (
            <div key={dateLabel} className="chat__day-group">
              <div className="chat__date-divider">
                <span>{dateLabel}</span>
              </div>
              {items.map((message) => (
                <article key={message.id} className={`chat__msg chat__msg--${message.role}`}>
                  <div className="chat__bubble">
                    <p>{message.content}</p>
                  </div>
                  <footer className="chat__meta">
                    <time className="chat__time" dateTime={message.timestamp.toISOString()}>
                      {formatTime(message.timestamp)}
                    </time>
                    <div className="chat__actions" role="group" aria-label="Message actions">
                      <button type="button">Copy</button>
                      <button type="button">Pin</button>
                      <button type="button">Flag</button>
                    </div>
                  </footer>
                </article>
              ))}
            </div>
          ))}
        </div>

        <div className="chat__composer" aria-label="Message composer">
          <div className="chat__composer-inner">
            <textarea
              placeholder="Share an update or ask Diriyah Brain AI to analyse project data..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              rows={1}
            />
            <div className="chat__controls">
              <div className="chat__attachments">
                <input
                  type="file"
                  ref={uploadInputRef}
                  className="chat__hidden-input"
                  onChange={handleUpload}
                />
                <button type="button" onClick={() => uploadInputRef.current?.click()} aria-label="Upload file">
                  <IconUpload />
                </button>
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  ref={cameraInputRef}
                  className="chat__hidden-input"
                  onChange={handleCameraCapture}
                />
                <button type="button" onClick={() => cameraInputRef.current?.click()} aria-label="Capture image">
                  <IconCamera />
                </button>
              </div>
              <button
                type="button"
                className={`chat__mic ${!micSupported ? "chat__mic--disabled" : ""}`}
                onClick={handleMicToggle}
                disabled={!micSupported}
                aria-pressed={isListening}
              >
                <IconMic active={isListening} />
              </button>
              <button type="button" className="chat__send" onClick={sendMessage}>
                Send
              </button>
            </div>
          </div>
          {!micSupported && (
            <p className="chat__mic-warning">Speech capture is not available in this browser.</p>
          )}
        </div>
      </main>

      <aside className={`context-panel ${isPanelOpen ? "context-panel--open" : ""}`} aria-label="Context panel">
        <div className="context-panel__tabs" role="tablist">
          <button type="button" role="tab" aria-selected="true">
            Documents
          </button>
          <button type="button" role="tab" aria-selected="false">
            Drawings
          </button>
          <button type="button" role="tab" aria-selected="false">
            Schedules
          </button>
          <button type="button" role="tab" aria-selected="false">
            Contracts
          </button>
        </div>
        <div className="context-panel__content">
          <h3>Project context</h3>
          <p>
            Summaries and risk dashboards from Google Drive, Aconex, and Primavera will appear here when the
            workspace is engaged.
          </p>
        </div>
      </aside>
    </div>
  );
}

export default App;
