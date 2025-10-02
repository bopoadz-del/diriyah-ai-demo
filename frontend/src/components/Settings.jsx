import React from "react";

export default function Settings() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-gray-900">Settings</h2>
        <p className="mt-2 text-gray-600">Manage your profile, notification preferences, and integrations.</p>
      </header>

      <div className="rounded-xl border border-gray-200 bg-white/90 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800">Profile</h3>
        <p className="mt-2 text-sm text-gray-600">Update your display information for collaborators.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-gray-700">
            Display Name
            <input
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-[#a67c52] focus:outline-none"
              defaultValue="Khalid"
            />
          </label>
          <label className="text-sm text-gray-700">
            Role
            <input
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-[#a67c52] focus:outline-none"
              defaultValue="Engineer"
            />
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white/90 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800">Integrations</h3>
        <p className="mt-2 text-sm text-gray-600">Connect file storage or scheduling tools to accelerate collaboration.</p>
        <ul className="mt-4 space-y-2 text-sm text-gray-600">
          <li>Google Drive (coming soon)</li>
          <li>SharePoint (coming soon)</li>
          <li>MS Teams notifications (coming soon)</li>
        </ul>
      </div>
    </section>
  );
}
