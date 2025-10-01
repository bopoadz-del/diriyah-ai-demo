import { useEffect, useMemo, useState } from "react";

export default function ProjectDashboard({ project }) {
  const [details, setDetails] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!project?.id) {
      setDetails(null);
      setStatus("idle");
      setError(null);
      return;
    }

    let cancelled = false;
    const fetchDetails = async () => {
      setStatus("loading");
      setError(null);
      try {
        const response = await fetch(`/api/projects/${project.id}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch project: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setDetails(payload?.project ?? project);
          setStatus("ready");
        }
      } catch (err) {
        console.error("Unable to load project details", err);
        if (!cancelled) {
          setDetails(project);
          setError(err instanceof Error ? err.message : "Unknown error");
          setStatus("error");
        }
      }
    };

    fetchDetails();
    return () => {
      cancelled = true;
    };
  }, [project?.id]);

  const summary = useMemo(() => {
    return details?.summary || "Select a project to see the latest status and key milestones.";
  }, [details?.summary]);

  if (!project?.id) {
    return (
      <section className="info-card">
        <h2 className="info-card__title">Project overview</h2>
        <p className="info-card__description">Pick a project from the left to load diagnostics.</p>
      </section>
    );
  }

  return (
    <section className="info-card">
      <div className="info-card__header">
        <div>
          <h2 className="info-card__title">{details?.name || project.name}</h2>
          <p className="info-card__description">{summary}</p>
        </div>
        <span className="badge">{details?.status || project.status || "Unknown"}</span>
      </div>

      <dl className="info-grid">
        <div>
          <dt>Location</dt>
          <dd>{details?.location || "—"}</dd>
        </div>
        <div>
          <dt>Drive folder</dt>
          <dd>{details?.drive_id || "—"}</dd>
        </div>
        <div>
          <dt>Progress</dt>
          <dd>{details?.progress_percent != null ? `${details.progress_percent}%` : "—"}</dd>
        </div>
        <div>
          <dt>Next milestone</dt>
          <dd>{details?.next_milestone || "—"}</dd>
        </div>
      </dl>

      {status === "loading" ? (
        <p className="info-card__footer">Refreshing project details…</p>
      ) : null}
      {error ? (
        <p className="info-card__footer error">{error}</p>
      ) : null}
    </section>
  );
}
