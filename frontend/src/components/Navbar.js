import React, { useRef, useState } from "react";
import { FileText, Bell, BarChart2, Settings as SettingsIcon, Layout } from "lucide-react";
const Navbar = () => {
  const fileInputRef = useRef(null);
  const [alerts, setAlerts] = useState([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const handleFileChange = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    const formData = new FormData(); formData.append("file", file);
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json(); alert(`File uploaded. Result: ${JSON.stringify(data.result)}`);
  };
  const fetchAlerts = async () => {
    const res = await fetch("/api/alerts/recent"); const data = await res.json(); setAlerts(data); setShowAlerts(!showAlerts);
  };
  return (
    <div className="navbar">
      <button onClick={() => fileInputRef.current.click()}><FileText size={16} className="inline-block mr-1" /> Docs</button>
      <input type="file" style={{ display: "none" }} ref={fileInputRef} onChange={handleFileChange} />
      <button onClick={fetchAlerts}><Bell size={16} className="inline-block mr-1" /> Notifications</button>
      {showAlerts && (<div className="dropdown">{alerts.map((a, i) => (<p key={i} className={a.level}>{a.message}</p>))}</div>)}
      <button onClick={() => window.location.href="/analytics"}><BarChart2 size={16} className="inline-block mr-1" /> Analytics</button>
      <button onClick={() => window.location.href="/settings"}><SettingsIcon size={16} className="inline-block mr-1" /> Settings</button>
      <button onClick={() => window.location.href="/split"}><Layout size={16} className="inline-block mr-1" /> Split View</button>
    </div>
  );
};
export default Navbar;
