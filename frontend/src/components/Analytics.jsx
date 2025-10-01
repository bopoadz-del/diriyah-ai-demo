import { useEffect, useState } from "react";

export default function Analytics({ projectId }) {
  const [summary, setSummary] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const loadSummary = async () => {
      setStatus("loading");
      setError(null);
      try {
        const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
        const response = await fetch(`/api/analytics/summary${suffix}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch analytics: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setSummary(payload?.data ?? {});
          setStatus("ready");
        }
      } catch (err) {
        console.error("Unable to load analytics", err);
        if (!cancelled) {
          setStatus("error");
          setError(err instanceof Error ? err.message : "Unknown error");
          setSummary(null);
        }
      }
    };

    loadSummary();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <section className="info-card">
      <div className="info-card__header">
        <div>
          <h2 className="info-card__title">Delivery metrics</h2>
          <p className="info-card__description">
            Lightweight analytics to validate the Render deployment and API connectivity.
          </p>
        </div>
        <span className="badge">{status === "loading" ? "Syncing" : "Live"}</span>
      </div>

      <div className="metric-grid">
        {summary ? (
          Object.entries(summary).map(([label, value]) => (
            <div key={label} className="metric-card">
              <div className="metric-label">{label}</div>
              <div className="metric-value">{String(value)}</div>
            </div>
          ))
        ) : (
          <div className="metric-empty">No analytics available yet.</div>
        )}
      </div>

      {error ? <p className="info-card__footer error">{error}</p> : null}
    </section>
  );
}
