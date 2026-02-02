import React from "react";

const highlights = [
  {
    title: "Schedule Health",
    value: "On Track",
    detail: "92% milestone adherence",
  },
  {
    title: "Budget Status",
    value: "Green",
    detail: "3.4% under baseline",
  },
  {
    title: "Active Risks",
    value: "4",
    detail: "2 require mitigation",
  },
];

const upcomingReviews = [
  "Facade procurement checkpoint — Oct 12",
  "Utilities integration sync — Oct 15",
  "Stakeholder walkthrough — Oct 20",
];

export default function ProjectDashboard() {
  return (
    <section className="mx-auto w-full max-w-6xl space-y-8 px-6 py-10">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Portfolio Overview</p>
        <h1 className="text-3xl font-semibold text-gray-900">Project Dashboard</h1>
        <p className="text-sm text-gray-600">
          Track delivery milestones, budget posture, and risk signals across the Diriyah program.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {highlights.map((item) => (
          <article
            key={item.title}
            className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{item.title}</p>
            <p className="mt-2 text-2xl font-semibold text-gray-900">{item.value}</p>
            <p className="mt-1 text-sm text-gray-600">{item.detail}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <section className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Workstream Pulse</h2>
          <p className="mt-2 text-sm text-gray-600">
            AI triage of delivery updates, procurement notes, and stakeholder feedback.
          </p>
          <div className="mt-4 space-y-4 text-sm text-gray-600">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="font-semibold text-gray-800">Package A — Cultural Core</p>
              <p>RFI closure rate improved to 87% after vendor alignment workshops.</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="font-semibold text-gray-800">Package B — Mobility</p>
              <p>Critical path watch: utilities tie-in requires updated access permits.</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="font-semibold text-gray-800">Package C — Hospitality</p>
              <p>Interior mock-up sign-off scheduled with design committee.</p>
            </div>
          </div>
        </section>

        <aside className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Upcoming Reviews</h2>
          <ul className="mt-4 space-y-3 text-sm text-gray-600">
            {upcomingReviews.map((item) => (
              <li key={item} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                {item}
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </section>
  );
}
