import { useEffect, useState } from "react";

export default function AlertsPanel({ projectId, className = "" }) {
  const [alerts, setAlerts] = useState([]);
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const loadAlerts = async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await fetch("/api/alerts/recent");
      if (!response.ok) {
        throw new Error(`Failed to load alerts: ${response.status}`);
      }
      const payload = await response.json();
      setAlerts(Array.isArray(payload) ? payload : []);
      setStatus("ready");
    } catch (err) {
      console.error("Unable to load alerts", err);
      setStatus("error");
      setAlerts([]);
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const submitAlert = async event => {
    event.preventDefault();
    if (!message.trim()) return;

    setStatus("submitting");
    setError(null);
    try {
      const response = await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim() }),
      });
      if (!response.ok) {
        throw new Error(`Failed to submit alert: ${response.status}`);
      }
      const payload = await response.json();
      setAlerts(prev => [payload, ...prev].slice(0, 5));
      setMessage("");
      setStatus("ready");
    } catch (err) {
      console.error("Unable to send alert", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  };

  return (
    <section className={`info-card ${className}`.trim()}>
      <div className="info-card__header">
        <div>
          <h2 className="info-card__title">Alerts</h2>
          <p className="info-card__description">
            Monitor project signals and send manual alerts for the delivery team.
          </p>
        </div>
        <span className="badge secondary">{alerts.length || 0} active</span>
      </div>

      <form className="alert-form" onSubmit={submitAlert}>
        <input
          className="alert-input"
          value={message}
          onChange={event => setMessage(event.target.value)}
          placeholder={projectId ? `Notify team about ${projectId}…` : "Post a status update…"}
        />
        <button type="submit" className="alert-button" disabled={!message.trim() || status === "submitting"}>
          {status === "submitting" ? "Sending…" : "Send"}
        </button>
      </form>

      <ul className="alerts-list">
        {alerts.map((alert, index) => (
          <li key={`${alert.message}-${index}`} className={`alert-item level-${alert.level || "info"}`}>
            <div className="alert-message">{alert.message}</div>
            <div className="alert-meta">{alert.status || "ok"}</div>
          </li>
        ))}
      </ul>

      {status === "loading" ? (
        <p className="info-card__footer">Loading alerts…</p>
      ) : null}
      {error ? <p className="info-card__footer error">{error}</p> : null}
    </section>
  );
}
