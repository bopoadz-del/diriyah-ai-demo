import { useEffect, useState } from "react";

const DEFAULT_PREFS = {
  notifications: true,
  driveSync: "daily",
  language: "en",
};

export default function Settings({ user }) {
  const userId = user?.id ?? "demo";
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [status, setStatus] = useState({ state: "idle", message: "" });

  useEffect(() => {
    let cancelled = false;
    const loadPreferences = async () => {
      try {
        const res = await fetch(`/api/preferences/${userId}`);
        if (!res.ok) throw new Error(`preferences fetch failed: ${res.status}`);
        const payload = await res.json();
        if (!cancelled) {
          setPrefs({ ...DEFAULT_PREFS, ...payload });
        }
      } catch (err) {
        console.warn("Failed to load preferences", err);
        if (!cancelled) {
          setStatus({ state: "error", message: "Using default preferences" });
          setPrefs(DEFAULT_PREFS);
        }
      }
    };
    loadPreferences();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const updatePref = (key, value) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  };

  const save = async (event) => {
    event.preventDefault();
    try {
      setStatus({ state: "saving", message: "" });
      const res = await fetch(`/api/preferences/${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
      });
      if (!res.ok) throw new Error(`save failed: ${res.status}`);
      setStatus({ state: "saved", message: "Preferences updated" });
    } catch (err) {
      console.warn("Failed to save preferences", err);
      setStatus({ state: "error", message: "Could not update preferences" });
    }
  };

  return (
    <section className="card p-6 max-w-3xl mx-auto">
      <header className="mb-6">
        <p className="section-title mb-1">Workspace settings</p>
        <h2 className="text-2xl font-semibold text-slate-900">Personalise your Diriyah Brain experience</h2>
        <p className="text-sm text-slate-500 mt-2">
          Preferences are stored in-memory for debugging on Render – perfect for validating UI flows without
          touching production services.
        </p>
      </header>

      <form className="space-y-6" onSubmit={save}>
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Notifications</h3>
          <label className="flex items-center gap-3 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={Boolean(prefs.notifications)}
              onChange={(event) => updatePref("notifications", event.target.checked)}
            />
            Email me when new Drive documents are indexed
          </label>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Drive synchronisation</h3>
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={prefs.driveSync}
            onChange={(event) => updatePref("driveSync", event.target.value)}
          >
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-2">Interface language</h3>
          <select
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={prefs.language}
            onChange={(event) => updatePref("language", event.target.value)}
          >
            <option value="en">English</option>
            <option value="ar">Arabic</option>
          </select>
        </div>

        <div className="flex items-center justify-between">
          <button
            type="submit"
            className="px-5 py-2 rounded-lg bg-slate-900 text-white text-sm font-semibold shadow hover:bg-slate-700"
            disabled={status.state === "saving"}
          >
            {status.state === "saving" ? "Saving…" : "Save preferences"}
          </button>
          {status.message && (
            <span
              className={`text-sm ${
                status.state === "saved"
                  ? "text-emerald-600"
                  : status.state === "error"
                  ? "text-rose-600"
                  : "text-slate-500"
              }`}
            >
              {status.message}
            </span>
          )}
        </div>
      </form>
    </section>
  );
}
