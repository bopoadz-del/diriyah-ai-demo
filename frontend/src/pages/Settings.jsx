import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

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

const intelligenceCapabilities = [
  {
    title: "Document Summarization",
    description: "Automatically generate concise summaries of lengthy Aconex documents and contracts so stakeholders grasp key changes at a glance.",
  },
  {
    title: "Contract Analysis",
    description: "Extract critical clauses, milestone dates, and obligations from legal agreements to keep commercial teams aligned on deliverables.",
  },
  {
    title: "Meeting Transcription & Action Items",
    description: "Transcribe coordination meetings and route AI-suggested action items back into workstreams for fast follow-up.",
  },
  {
    title: "Sentiment Analysis",
    description: "Monitor stakeholder communications to surface emerging risks and sentiment shifts before they impact delivery timelines.",
  },
];

const STATUS_STYLES = {
  checking: {
    badge: "bg-amber-500",
    label: "Checking connection",
  },
  online: {
    badge: "bg-emerald-500",
    label: "Connected to backend",
  },
  offline: {
    badge: "bg-rose-500",
    label: "Backend unreachable",
  },
};

export default function Settings() {
  const [backendStatus, setBackendStatus] = useState({
    state: "checking",
    message: "Pinging health endpoint...",
    lastChecked: null,
  });

  const timestampLabel = useMemo(() => {
    if (!backendStatus.lastChecked) {
      return "Never";
    }

    return backendStatus.lastChecked.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }, [backendStatus.lastChecked]);

  const checkBackend = useCallback(async () => {
    setBackendStatus((prev) => ({ ...prev, state: "checking", message: "Pinging health endpoint..." }));

    try {
      const response = await apiFetch("/api/health", { cache: "no-store" });

      if (!response.ok) {
        throw new Error(`Received status ${response.status}`);
      }

      const payload = await response.json().catch(() => ({ status: "ok" }));
      const detailMessage = payload.status || payload.message || "Backend responded successfully.";

      setBackendStatus({
        state: "online",
        message: detailMessage,
        lastChecked: new Date(),
      });
    } catch (error) {
      setBackendStatus({
        state: "offline",
        message: error instanceof Error ? error.message : "Unknown error occurred",
        lastChecked: new Date(),
      });
    }
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  const statusMeta = STATUS_STYLES[backendStatus.state] ?? STATUS_STYLES.checking;

  return (
    <section className="mx-auto w-full max-w-5xl space-y-8 px-6 py-10">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Workspace Settings</p>
        <h2 className="mt-2 text-3xl font-semibold text-gray-900">Settings</h2>
        <p className="mt-2 text-sm text-gray-600">
          Manage your profile, security posture, and data governance policies.
        </p>
      </header>

      <div className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Platform Diagnostics</h3>
            <p className="mt-1 text-sm text-gray-600">
              Confirm backend availability before enabling automation or compliance workflows.
            </p>
          </div>
          <button
            type="button"
            onClick={checkBackend}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-[#a67c52] hover:text-[#a67c52] focus:outline-none focus:ring-2 focus:ring-[#a67c52] focus:ring-offset-2"
          >
            Refresh status
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <span className={`h-3 w-3 shrink-0 rounded-full ${statusMeta.badge}`} aria-hidden="true" />
              <div>
                <p className="text-sm font-medium text-gray-800">{statusMeta.label}</p>
                <p className="text-xs text-gray-600">{backendStatus.message}</p>
              </div>
            </div>
            <p className="text-xs text-gray-500">Last checked: {timestampLabel}</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm">
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
            <article key={item.title} className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm">
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
            <article key={item.title} className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm">
              <h4 className="text-base font-semibold text-gray-800">{item.title}</h4>
              <p className="mt-2 text-sm text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <header>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Intelligent Workflows</p>
          <h3 className="text-xl font-semibold text-gray-900">AI assistance for documents and communications</h3>
          <p className="mt-2 text-sm text-gray-600">
            Built-in language intelligence summarizes long-form content, pinpoints contractual obligations, and tracks conversation sentiment to speed up decision-making.
          </p>
        </header>
        <div className="grid gap-4 md:grid-cols-2">
          {intelligenceCapabilities.map((item) => (
            <article key={item.title} className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm">
              <h4 className="text-base font-semibold text-gray-800">{item.title}</h4>
              <p className="mt-2 text-sm text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
