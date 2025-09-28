import React, { useEffect, useState } from "react";
const Settings = ({ userId = "user1" }) => {
  const [prefs, setPrefs] = useState({});
  useEffect(() => { fetch(`/api/preferences/${userId}`).then((res) => res.json()).then((data) => setPrefs(data)); }, [userId]);
  const savePrefs = async () => { await fetch(`/api/preferences/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(prefs), }); alert("Preferences saved"); };
  return (
    <div><h3>Settings</h3>
      <label>Theme:<select value={prefs.theme || ""} onChange={(e) => setPrefs({ ...prefs, theme: e.target.value })}><option value="diriyah">Diriyah</option><option value="light">Light</option><option value="dark">Dark</option></select></label><br />
      <label>Alerts:<input type="checkbox" checked={prefs.alerts || false} onChange={(e) => setPrefs({ ...prefs, alerts: e.target.checked })} /></label><br />
      <button onClick={savePrefs}>Save</button>
    </div>
  );
};
export default Settings;
