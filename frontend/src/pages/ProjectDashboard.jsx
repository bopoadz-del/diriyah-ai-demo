import React from "react";

const highlights = [
  {
    title: "Schedule confidence",
    value: "92%",
    detail: "Milestones for Q2 remain on track with no critical path shifts.",
  },
  {
    title: "Active workstreams",
    value: "14",
    detail: "Structural, landscape, MEP, and retail fit-out teams reporting.",
  },
  {
    title: "Open risks",
    value: "6",
    detail: "Two items require executive review before next checkpoint.",
  },
];

const updates = [
  {
    title: "Foundation package",
    detail: "Pile cap inspections completed and signed off by QA/QC.",
  },
  {
    title: "Utilities corridor",
    detail: "MEP coordination meeting scheduled with vendors for Monday.",
  },
  {
    title: "Guest experience",
    detail: "Wayfinding prototypes approved for fabrication.",
  },
];

export default function ProjectDashboard() {
  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Dashboard</p>
        <h2 className="text-2xl font-semibold text-gray-900">Project delivery overview</h2>
        <p className="text-sm text-gray-600">
          Track status across the Diriyah portfolio and stay ahead of risk trends.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {highlights.map((item) => (
          <article key={item.title} className="rounded-xl border border-gray-200 bg-gray-50 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{item.title}</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{item.value}</p>
            <p className="mt-2 text-sm text-gray-600">{item.detail}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Latest updates</h3>
          <div className="space-y-3">
            {updates.map((update) => (
              <article key={update.title} className="rounded-xl border border-gray-200 bg-white p-4">
                <h4 className="text-sm font-semibold text-gray-800">{update.title}</h4>
                <p className="mt-2 text-sm text-gray-600">{update.detail}</p>
              </article>
            ))}
          </div>
        </section>
        <aside className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">Upcoming milestones</h3>
          <ul className="space-y-3">
            <li className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-sm font-semibold text-gray-800">Retail district handover</p>
              <p className="mt-2 text-xs text-gray-500">Feb 14 · Package A</p>
            </li>
            <li className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-sm font-semibold text-gray-800">Zone 2 landscaping</p>
              <p className="mt-2 text-xs text-gray-500">Feb 20 · Package C</p>
            </li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
