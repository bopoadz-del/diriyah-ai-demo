import React, { useEffect, useState } from "react";
const Settings = ({ userId = "user1" }) => {
  const [prefs, setPrefs] = useState({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    let isMounted = true;
    const loadPrefs = async () => {
      try {
        const response = await fetch(`/api/preferences/${userId}`);
        if (!response.ok) throw new Error(`Failed to load preferences (${response.status})`);
        const data = await response.json();
        if (isMounted) setPrefs(data);
      } catch (prefsError) {
        console.error("Failed to load preferences", prefsError);
        if (isMounted) setStatus("Unable to load preferences.");
      }
    };
    loadPrefs();
    return () => { isMounted = false; };
  }, [userId]);

  const updatePref = (key, value) => { setPrefs((prev) => ({ ...prev, [key]: value })); };

  const savePrefs = async () => {
    try {
      const response = await fetch(`/api/preferences/${userId}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(prefs),
      });
      if (!response.ok) throw new Error(`Failed to save preferences (${response.status})`);
      setStatus("Preferences saved.");
    } catch (saveError) {
      console.error("Failed to save preferences", saveError); setStatus("Unable to save preferences. Please try again.");
    }
  };

  return (
    <div className="settings-panel">
      <h3>Settings</h3>
      <label className="settings-field">Theme:
        <select value={prefs.theme ?? "diriyah"} onChange={(event) => updatePref("theme", event.target.value)}>
          <option value="diriyah">Diriyah</option><option value="light">Light</option><option value="dark">Dark</option>
        </select>
      </label>
      <label className="settings-field">Alerts:
        <input type="checkbox" checked={Boolean(prefs.alerts)} onChange={(event) => updatePref("alerts", event.target.checked)} />
      </label>
      <button type="button" onClick={savePrefs}>Save</button>
      {status && <p className="settings-status">{status}</p>}
    </div>
  );
};
export default Settings;
