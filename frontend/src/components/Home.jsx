import React from "react";

export default function Home() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-10">
      <h2 className="text-2xl font-semibold text-gray-900">Welcome to Diriyah Brain AI</h2>
      <p className="mt-3 text-gray-600">
        Select a project from the sidebar or start a new chat to begin collaborating with your delivery team.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white/90 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800">Quick Actions</h3>
          <ul className="mt-3 list-disc pl-5 text-sm text-gray-600">
            <li>Review today's site activities</li>
            <li>Upload progress photos</li>
            <li>Share updates with stakeholders</li>
          </ul>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white/90 p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800">Latest Highlights</h3>
          <p className="mt-3 text-sm text-gray-600">
            Villa 100 pour sequence signed off. Logistics for Cultural District revised with overnight deliveries.
          </p>
        </div>
      </div>
    </section>
  );
}
