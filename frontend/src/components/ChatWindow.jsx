import React from "react";
import { Link } from "react-router-dom";

function ChatWindow({ messages }) {
  return (
    <div className="p-4 space-y-3">
      {messages.map((m, i) => (
        <div key={i}>{m.text}</div>
      ))}
      {messages.length > 0 && messages[messages.length-1].alerts &&
        messages[messages.length-1].alerts.map((a, idx) => (
          <div key={idx} className="p-3 bg-red-50 border">
            ⚠️ [{a.category}] {a.message}
            {a.project_id && a.project_id !== 0 && (
              <Link to={`/projects/${a.project_id}`} className="text-blue-600 underline ml-2">View Project</Link>
            )}
          </div>
        ))
      }
    </div>
  );
}
export default ChatWindow;
