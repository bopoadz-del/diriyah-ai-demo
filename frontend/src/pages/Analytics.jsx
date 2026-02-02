import React from "react";

const kpis = [
  { label: "Active Workstreams", value: "18", delta: "+3" },
  { label: "Weekly RFIs", value: "126", delta: "-8" },
  { label: "Average Response", value: "1.6d", delta: "-0.4d" },
  { label: "Open NCRs", value: "12", delta: "+1" },
];

const insights = [
  {
    title: "Materials Lead Time",
    description: "Imported stone delivery windows narrowed by 12% after vendor consolidation.",
  },
  {
    title: "Safety Compliance",
    description: "Weekly safety walk scores rose to 94% with focused toolbox training.",
  },
  {
    title: "Design Coordination",
    description: "Model clashes down 18% after integrating MEP weekly clash reviews.",
  },
];

export default function Analytics() {
  return (
    <section className="mx-auto w-full max-w-6xl space-y-8 px-6 py-10">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Portfolio Analytics</p>
        <h1 className="text-3xl font-semibold text-gray-900">Program Performance</h1>
        <p className="text-sm text-gray-600">
          Live indicators across delivery, compliance, and stakeholder communications.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <article key={kpi.label} className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{kpi.label}</p>
            <div className="mt-3 flex items-baseline justify-between">
              <span className="text-2xl font-semibold text-gray-900">{kpi.value}</span>
              <span className="text-xs font-semibold text-emerald-600">{kpi.delta}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <section className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Trend Highlights</h2>
          <p className="mt-2 text-sm text-gray-600">
            AI-curated insights from delivery logs, RFIs, and stakeholder reports.
          </p>
          <div className="mt-4 space-y-4">
            {insights.map((insight) => (
              <div key={insight.title} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-800">{insight.title}</h3>
                <p className="mt-2 text-sm text-gray-600">{insight.description}</p>
              </div>
            ))}
          </div>
        </section>

        <aside className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Reporting Pulse</h2>
          <div className="mt-4 space-y-3 text-sm text-gray-600">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="font-semibold text-gray-800">Weekly dashboards</p>
              <p>Automated snapshots delivered to program leadership every Monday.</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="font-semibold text-gray-800">Risk forecasts</p>
              <p>Next 30-day forecast indicates low exposure across mobility and hospitality.</p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
