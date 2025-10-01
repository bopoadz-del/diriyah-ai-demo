import { useEffect, useState } from "react";

const USER_ID = "render-debugger";

const DEFAULT_PREFS = {
  display_name: "Render Debugger",
  notifications: true,
  theme: "light",
  active_project: null,
};

export default function Settings({ activeProjectId }) {
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [status, setStatus] = useState("idle");
  const [projects, setProjects] = useState([]);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const loadPrefs = async () => {
      try {
        const response = await fetch(`/api/preferences/${USER_ID}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch preferences: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setPrefs(prev => ({ ...prev, ...payload }));
        }
      } catch (err) {
        console.error("Unable to load preferences", err);
      }
    };

    const loadProjects = async () => {
      try {
        const response = await fetch("/api/projects");
        if (!response.ok) {
          throw new Error(`Failed to fetch projects: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setProjects(Array.isArray(payload?.projects) ? payload.projects : []);
        }
      } catch (err) {
        console.error("Unable to load projects", err);
      }
    };

    loadPrefs();
    loadProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (activeProjectId && prefs.active_project !== activeProjectId) {
      setPrefs(prev => ({ ...prev, active_project: activeProjectId }));
    }
  }, [activeProjectId, prefs.active_project]);

  const updatePref = (key, value) => {
    setPrefs(prev => ({ ...prev, [key]: value }));
  };

  const save = async event => {
    event.preventDefault();
    setStatus("saving");
    setMessage(null);
    try {
      const response = await fetch(`/api/preferences/${USER_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      });
      if (!response.ok) {
        throw new Error(`Failed to save preferences: ${response.status}`);
      }
      await response.json();
      setStatus("saved");
      setMessage("Preferences saved. Context updated for backend services.");
    } catch (err) {
      console.error("Unable to save preferences", err);
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Unknown error");
    }
  };

  return (
    <section className="info-card">
      <div className="info-card__header">
        <div>
          <h2 className="info-card__title">User preferences</h2>
          <p className="info-card__description">
            Persisted in memory for Render debugging. Saving updates the global project context.
          </p>
        </div>
        <span className="badge">{status === "saving" ? "Saving" : "Editable"}</span>
      </div>

      <form className="settings-form" onSubmit={save}>
        <label className="settings-field">
          <span>Display name</span>
          <input
            type="text"
            value={prefs.display_name ?? ""}
            onChange={event => updatePref("display_name", event.target.value)}
          />
        </label>

        <label className="settings-field">
          <span>Theme</span>
          <select value={prefs.theme ?? "light"} onChange={event => updatePref("theme", event.target.value)}>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="auto">Auto</option>
          </select>
        </label>

        <label className="settings-field toggle">
          <span>Email notifications</span>
          <input
            type="checkbox"
            checked={Boolean(prefs.notifications)}
            onChange={event => updatePref("notifications", event.target.checked)}
          />
        </label>

        <label className="settings-field">
          <span>Active project</span>
          <select
            value={prefs.active_project ?? ""}
            onChange={event => updatePref("active_project", event.target.value || null)}
          >
            <option value="">No project</option>
            {projects.map(item => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <button type="submit" className="settings-submit" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : "Save preferences"}
        </button>
      </form>

      {message ? (
        <p className={`info-card__footer ${status === "error" ? "error" : ""}`}>{message}</p>
      ) : null}
    </section>
  );
}
