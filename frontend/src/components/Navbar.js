import React, { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Bell,
  BarChart2,
  Settings as SettingsIcon,
  Layout,
} from "lucide-react";

const Navbar = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [alerts, setAlerts] = useState([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = useCallback(async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed (${response.status})`);
      }

      const payload = await response.json();
      window.alert(
        `File uploaded successfully. Result: ${JSON.stringify(payload.result)}`,
      );
    } catch (uploadError) {
      console.error("Failed to upload file", uploadError);
      setError("Unable to upload file. Please try again.");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }, []);

  const toggleAlerts = useCallback(async () => {
    if (showAlerts) {
      setShowAlerts(false);
      return;
    }

    try {
      const response = await fetch("/api/alerts/recent");
      if (!response.ok) {
        throw new Error(`Failed to fetch alerts (${response.status})`);
      }

      const data = await response.json();
      setAlerts(Array.isArray(data) ? data : []);
      setShowAlerts(true);
    } catch (alertsError) {
      console.error("Failed to fetch alerts", alertsError);
      setError("Unable to load alerts.");
    }
  }, [showAlerts]);

  return (
    <div className="navbar" role="navigation" aria-label="Primary">
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        <FileText size={16} className="inline-block mr-1" />
        {isUploading ? "Uploading…" : "Docs"}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <button type="button" onClick={toggleAlerts}>
        <Bell size={16} className="inline-block mr-1" /> Notifications
      </button>
      {showAlerts && (
        <div className="dropdown" role="status" aria-live="polite">
          {alerts.map((alert, index) => (
            <p key={`${alert.message}-${index}`} className={alert.level}>
              {alert.message}
            </p>
          ))}
          {alerts.length === 0 && <p>No alerts available.</p>}
        </div>
      )}

      <button type="button" onClick={() => navigate("/analytics")}>
        <BarChart2 size={16} className="inline-block mr-1" /> Analytics
      </button>
      <button type="button" onClick={() => navigate("/settings")}>
        <SettingsIcon size={16} className="inline-block mr-1" /> Settings
      </button>
      <button type="button" onClick={() => navigate("/split")}>
        <Layout size={16} className="inline-block mr-1" /> Split View
      </button>

      {error && <p className="navbar-error">{error}</p>}
    </div>
  );
};

export default Navbar;
