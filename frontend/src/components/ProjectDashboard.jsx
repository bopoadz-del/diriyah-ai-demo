export default function ProjectDashboard({ project }) {
  if (!project) {
    return (
      <section className="card text-sm text-slate-500">
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Project overview</h2>
        <p>Select a project on the left to see context.</p>
      </section>
    );
  }

  const details = [
    { label: "Project ID", value: project.id },
    { label: "Location", value: project.location },
    { label: "Next milestone", value: project.next_milestone },
  ].filter((item) => item.value);

  const progress = Number(project.progress_percent ?? project.progress ?? 0);

  return (
    <section className="card">
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Project overview</h2>
        {project.summary && <p className="text-sm text-slate-500 mt-1">{project.summary}</p>}
      </header>

      <div className="mb-5">
        <div className="flex items-center justify-between mb-2 text-sm text-slate-600">
          <span>Overall progress</span>
          <span className="font-semibold text-slate-900">{progress}%</span>
        </div>
        <div className="h-3 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all"
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      </div>

      <dl className="space-y-2 text-sm">
        {details.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <dt className="text-slate-500">{item.label}</dt>
            <dd className="font-medium text-slate-900 text-right">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
