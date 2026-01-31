import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

const defaultPayload = {
  query: "Why was the foundation design changed last month?",
  goal: "Prepare for the structural inspection next week",
  context: {},
};

const FeatureCard = ({ feature }) => {
  const { id, title, summary, highlights, details } = feature;

  const formattedDetails = useMemo(() => {
    if (!details) {
      return null;
    }
    return JSON.stringify(details, null, 2);
  }, [details]);

  return (
    <article
      key={id}
      className="rounded-2xl border border-gray-200 bg-white/90 p-5 shadow-sm backdrop-blur"
    >
      <header className="mb-3">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="mt-1 text-sm text-gray-600">{summary}</p>
      </header>
      {Array.isArray(highlights) && highlights.length > 0 && (
        <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-gray-700">
          {highlights.map((item, index) => (
            <li key={`${id}-highlight-${index}`}>{item}</li>
          ))}
        </ul>
      )}
      {formattedDetails && (
        <details className="mt-2 group">
          <summary className="cursor-pointer text-sm font-medium text-[#a67c52]">
            Inspect structured output
          </summary>
          <pre className="mt-2 overflow-auto rounded-lg bg-gray-900/90 p-3 text-xs text-gray-100 shadow-inner">
            {formattedDetails}
          </pre>
        </details>
      )}
    </article>
  );
};

export default function AdvancedIntelligence() {
  const [payload, setPayload] = useState(defaultPayload);
  const [report, setReport] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runAnalysis = useCallback(async (inputPayload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch("/api/advanced-intelligence/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inputPayload),
      });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const data = await response.json();
      setReport(Array.isArray(data.results) ? data.results : []);
    } catch (requestError) {
      setError(requestError.message);
      setReport([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    runAnalysis(defaultPayload);
  }, [runAnalysis]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setPayload((previous) => ({ ...previous, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    runAnalysis(payload);
  };

  return (
    <section className="mx-auto w-full max-w-6xl px-6 py-10">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Advanced Intelligence Sandbox</h2>
          <p className="mt-1 text-sm text-gray-600">
            Experiment with the simulated advanced reasoning, planning, and analytics capabilities.
          </p>
        </div>
        <button
          type="button"
          onClick={() => runAnalysis(payload)}
          className="inline-flex items-center gap-2 rounded-md border border-transparent bg-[#a67c52] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#8f6843]"
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh insights"}
        </button>
      </header>

      <form
        onSubmit={handleSubmit}
        className="mb-8 grid gap-4 rounded-2xl border border-gray-200 bg-white/90 p-6 shadow-sm backdrop-blur"
      >
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700">
            Primary query
          </label>
          <textarea
            id="query"
            name="query"
            className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-[#a67c52] focus:outline-none"
            rows={2}
            value={payload.query}
            onChange={handleChange}
          />
        </div>
        <div>
          <label htmlFor="goal" className="block text-sm font-medium text-gray-700">
            Goal (optional)
          </label>
          <input
            id="goal"
            name="goal"
            type="text"
            className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-[#a67c52] focus:outline-none"
            value={payload.goal ?? ""}
            onChange={handleChange}
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            className="rounded-md border border-transparent bg-gray-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-gray-700"
            disabled={loading}
          >
            {loading ? "Generating..." : "Generate insights"}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {loading && report.length === 0 && (
          <p className="text-sm text-gray-500">Loading intelligence modules...</p>
        )}
        {!loading && report.length === 0 && !error && (
          <p className="text-sm text-gray-500">No insights available for the provided input.</p>
        )}
        {report.map((feature) => (
          <FeatureCard key={feature.id} feature={feature} />
        ))}
      </div>
    </section>
  );
}
