import { useEffect, useMemo, useState } from "react";

const FALLBACK_SUMMARY = {
  metrics: {
    documents_indexed: 128,
    alerts_open: 3,
    meetings_transcribed: 6,
    drive_sync: "2024-04-12T10:00:00Z",
    response_time_ms: 820,
    satisfaction: 92,
  },
  timeline: [
    { label: "Mon", value: 8 },
    { label: "Tue", value: 11 },
    { label: "Wed", value: 6 },
    { label: "Thu", value: 14 },
    { label: "Fri", value: 9 },
  ],
};

export default function Analytics({ project }) {
  const [summary, setSummary] = useState(FALLBACK_SUMMARY);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadSummary = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/analytics/summary");
        if (!res.ok) throw new Error(`analytics/summary failed: ${res.status}`);
        const payload = await res.json();
        if (!cancelled) {
          setSummary({
            metrics: payload.metrics || payload.data || FALLBACK_SUMMARY.metrics,
            timeline: payload.timeline || FALLBACK_SUMMARY.timeline,
          });
          setError("");
        }
      } catch (err) {
        console.warn("Failed to load analytics summary", err);
        if (!cancelled) {
          setSummary(FALLBACK_SUMMARY);
          setError("Using cached analytics snapshot");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadSummary();
    return () => {
      cancelled = true;
    };
  }, []);

  const metricEntries = useMemo(() => {
    const metrics = summary.metrics || {};
    return [
      { key: "documents_indexed", label: "Docs indexed", unit: "" },
      { key: "alerts_open", label: "Open alerts", unit: "" },
      { key: "meetings_transcribed", label: "Meetings transcribed", unit: "" },
      { key: "response_time_ms", label: "Avg. response", unit: "ms" },
      { key: "satisfaction", label: "Stakeholder satisfaction", unit: "%" },
      project?.progress_percent != null
        ? { key: "progress_percent", label: "Progress", value: project.progress_percent, unit: "%" }
        : null,
    ]
      .filter(Boolean)
      .map((entry) => ({
        ...entry,
        value:
          entry.value != null
            ? entry.value
            : metrics[entry.key] != null
            ? metrics[entry.key]
            : FALLBACK_SUMMARY.metrics[entry.key] ?? "–",
      }));
  }, [summary, project]);

  const timeline = summary.timeline || FALLBACK_SUMMARY.timeline;

  return (
    <section className="card p-6">
      <header className="flex items-center justify-between mb-6">
        <div>
          <p className="section-title mb-1">Project analytics</p>
          <h2 className="text-2xl font-semibold text-slate-900">
            {project?.name ? `${project.name} insight board` : "Operational insight board"}
          </h2>
        </div>
        <div className="text-xs text-slate-500">
          {loading ? "Refreshing…" : "Updated from backend"}
        </div>
      </header>

      {error && <p className="text-sm text-amber-600 mb-4">{error}</p>}

      <div className="metric-grid mb-8">
        {metricEntries.map((metric) => (
          <div key={metric.key} className="metric-card card px-5 py-4">
            <h3>{metric.label}</h3>
            <span>
              {metric.value}
              {metric.unit}
            </span>
          </div>
        ))}
      </div>

      <div>
        <p className="section-title mb-3">AI request timeline</p>
        <div className="card px-5 py-4">
          <div className="timeline">
            {timeline.map((point) => (
              <div
                key={point.label}
                className="timeline-bar"
                style={{ height: `${(point.value || 1) * 8}px` }}
                title={`${point.value} interactions`}
              >
                <span>{point.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
