import React from "react";

const securityControls = [
  {
    title: "RBAC Enhancements",
    description: "Assign granular permissions down to individual drawings, documents, and even specific data fields to keep teams focused on the work that matters to them.",
  },
  {
    title: "Audit Trail",
    description: "Capture every view, download, and update with immutable timestamps to satisfy contractual and regulatory compliance reviews.",
  },
  {
    title: "Data Encryption",
    description: "Protect sensitive submissions with end-to-end encryption covering data in transit between job sites and at rest in the workspace vault.",
  },
  {
    title: "SOC 2 / ISO 27001",
    description: "Operate against enterprise-grade controls, backed by third-party certifications and continuous monitoring of policy adherence.",
  },
  {
    title: "Watermarking",
    description: "Automatically watermark high-risk drawings and exports so downstream sharing remains traceable across contractors and consultants.",
  },
];

const privacyFeatures = [
  {
    title: "PII Detection",
    description: "Locate personal data inside uploaded photos, RFIs, and reports, then mask or redact it before it reaches broader project channels.",
  },
  {
    title: "Data Retention Policies",
    description: "Automate archival schedules and defensible deletion workflows aligned to client and regulatory obligations.",
  },
  {
    title: "GDPR Compliance",
    description: "Deliver right-to-be-forgotten, consent management, and data portability tooling for European partners and residents.",
  },
];

export default function Settings() {
  return (
    <section className="mx-auto w-full max-w-4xl px-6 py-10 space-y-6">
      <header>
        <h2 className="text-2xl font-semibold text-gray-900">Settings</h2>
        <p className="mt-2 text-gray-600">Manage your profile, security posture, and data governance policies.</p>
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

      <section className="space-y-4">
        <header>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Security &amp; Compliance</p>
          <h3 className="text-xl font-semibold text-gray-900">Enterprise safeguards for project data</h3>
          <p className="mt-2 text-sm text-gray-600">
            Layered controls help project admins enforce least-privilege access, prove compliance, and keep sensitive documentation protected at every step.
          </p>
        </header>
        <div className="grid gap-4 md:grid-cols-2">
          {securityControls.map((item) => (
            <article key={item.title} className="h-full rounded-xl border border-gray-200 bg-white/90 p-5 shadow-sm">
              <h4 className="text-base font-semibold text-gray-800">{item.title}</h4>
              <p className="mt-2 text-sm text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <header>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Privacy &amp; Data Governance</p>
          <h3 className="text-xl font-semibold text-gray-900">Automated controls for confidential information</h3>
          <p className="mt-2 text-sm text-gray-600">
            Advanced detection and retention tooling keeps personally identifiable information handled responsibly across global delivery teams.
          </p>
        </header>
        <div className="grid gap-4 md:grid-cols-2">
          {privacyFeatures.map((item) => (
            <article key={item.title} className="h-full rounded-xl border border-gray-200 bg-white/90 p-5 shadow-sm">
              <h4 className="text-base font-semibold text-gray-800">{item.title}</h4>
              <p className="mt-2 text-sm text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
