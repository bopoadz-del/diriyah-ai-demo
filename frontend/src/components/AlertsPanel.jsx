import { useEffect, useState } from "react";

const LEVEL_STYLES = {
  info: "bg-blue-50 text-blue-700 border border-blue-100",
  warning: "bg-amber-50 text-amber-700 border border-amber-100",
  error: "bg-rose-50 text-rose-700 border border-rose-100",
};

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const loadAlerts = async () => {
      try {
        const res = await fetch("/api/alerts/recent");
        if (!res.ok) throw new Error(`alerts/recent failed: ${res.status}`);
        const data = await res.json();
        if (!cancelled) setAlerts(data);
      } catch (err) {
        console.warn("Failed to fetch alerts", err);
        if (!cancelled) setError("Unable to load recent alerts");
      }
    };
    loadAlerts();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-slate-900">Live alerts</h2>
        <span className="text-xs text-slate-500 uppercase tracking-wide">
          Render debugging feed
        </span>
      </div>
      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}
      <div className="flex flex-col gap-2">
        {(alerts.length ? alerts : [{ message: "No alerts at the moment", level: "info" }]).map(
          (alert, index) => (
            <article
              key={`${alert.message}-${index}`}
              className={`rounded-xl px-3 py-2 text-sm ${LEVEL_STYLES[alert.level] || LEVEL_STYLES.info}`}
            >
              <p className="font-medium">{alert.message}</p>
              {alert.status && (
                <p className="text-xs opacity-70 mt-0.5">Status: {alert.status}</p>
              )}
            </article>
          ),
        )}
      </div>
    </section>
  );
}
