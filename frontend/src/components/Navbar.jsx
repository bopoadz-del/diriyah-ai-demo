export default function Navbar({ user, project, health, loadingProject }) {
  const healthStatus = (health?.status || "loading").toLowerCase();
  const healthLabel =
    healthStatus === "ok"
      ? "Backend healthy"
      : healthStatus === "error"
      ? health?.message || "Backend unavailable"
      : "Checking backend";

  return (
    <header className="flex items-center justify-between px-8 py-5 border-b border-slate-200/70 bg-white/80 backdrop-blur">
      <div className="flex items-center gap-4">
        <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 text-white flex items-center justify-center text-lg font-semibold shadow-lg">
          MB
        </div>
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Diriyah Brain AI</p>
          <h1 className="text-xl font-semibold text-slate-900">
            {project?.name || "Select a project"}
            {loadingProject && <span className="ml-2 text-sm text-slate-500">Loading…</span>}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3 text-sm">
        <span className={`pill pill-status-${healthStatus}`}>{healthLabel}</span>
        {project?.status && (
          <span className="pill bg-slate-100 text-slate-600">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
            {project.status}
          </span>
        )}
        {user && (
          <span className="pill bg-slate-900 text-white">
            <span role="img" aria-hidden="true">
              👋
            </span>
            {user.name}
          </span>
        )}
      </div>
    </header>
  );
}
