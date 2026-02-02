import React from "react";

const metrics = [
  { label: "Portfolio health", value: "Green", detail: "4 programs stable" },
  { label: "On-time delivery", value: "88%", detail: "+3% vs last week" },
  { label: "Budget variance", value: "-1.8%", detail: "Below target" },
  { label: "Open RFIs", value: "23", detail: "7 due this week" },
];

const insights = [
  {
    title: "Supply chain watch",
    detail: "Steel deliveries in Zone 3 are trending 5 days late. Confirm alternate vendors.",
  },
  {
    title: "Safety pulse",
    detail: "Zero incidents reported in the last 30 days across active sites.",
  },
  {
    title: "Cost guardrail",
    detail: "Closeout packages for Package B should be locked by Friday to protect margin.",
  },
];

export default function Analytics() {
  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Analytics</p>
        <h2 className="text-2xl font-semibold text-gray-900">Delivery intelligence</h2>
        <p className="text-sm text-gray-600">
          Monitor performance signals, cost trends, and operational insights across the program.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <article key={metric.label} className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{metric.label}</p>
            <p className="mt-2 text-xl font-semibold text-gray-900">{metric.value}</p>
            <p className="mt-1 text-xs text-gray-500">{metric.detail}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-lg font-semibold text-gray-900">Weekly signals</h3>
          <p className="mt-2 text-sm text-gray-600">
            Consolidated trendlines from workstream reports and automated site captures.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Schedule drift</p>
              <p className="mt-2 text-lg font-semibold text-gray-900">+2 days</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Change orders</p>
              <p className="mt-2 text-lg font-semibold text-gray-900">3 pending</p>
            </div>
          </div>
        </section>
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-lg font-semibold text-gray-900">Priority insights</h3>
          <div className="mt-4 space-y-3">
            {insights.map((insight) => (
              <article key={insight.title} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <h4 className="text-sm font-semibold text-gray-800">{insight.title}</h4>
                <p className="mt-2 text-sm text-gray-600">{insight.detail}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
