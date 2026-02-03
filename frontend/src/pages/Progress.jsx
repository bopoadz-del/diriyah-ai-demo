import React, { useState } from "react";
import { apiFetch } from "../lib/api";

export default function Progress() {
  const [location, setLocation] = useState("");
  const [progress, setProgress] = useState(0);
  const [scheduled, setScheduled] = useState(0);
  const [delays, setDelays] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [loadingDelays, setLoadingDelays] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submitSnapshot = async () => {
    setError(null);
    setStatus(null);
    if (!location.trim()) {
      setError("Please enter a location before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await apiFetch("/api/progress/snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location,
          progress: parseFloat(progress),
          scheduled_progress: parseFloat(scheduled),
        }),
      });
      if (!response.ok) {
        throw new Error(`Snapshot submission failed (${response.status})`);
      }
      setStatus("Snapshot recorded.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const loadDelays = async () => {
    setError(null);
    setStatus(null);
    if (!location.trim()) {
      setError("Enter a location to load delays.");
      return;
    }
    setLoadingDelays(true);
    try {
      const res = await apiFetch(`/api/progress/delays/${encodeURIComponent(location)}`);
      if (!res.ok) {
        throw new Error(`Failed to load delays (${res.status})`);
      }
      const data = await res.json();
      setDelays(data.delays || []);
      setStatus(`Loaded ${data.delays?.length ?? 0} delayed snapshots.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingDelays(false);
    }
  };

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Progress</p>
        <h2 className="text-2xl font-semibold text-gray-900">Progress Tracking</h2>
        <p className="text-sm text-gray-600">
          Record progress snapshots and review delayed activities by location.
        </p>
      </header>

      <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-semibold text-gray-700">
            Location
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
              placeholder="Zone A"
            />
          </label>
          <label className="text-sm font-semibold text-gray-700">
            Actual progress (0–1)
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={progress}
              onChange={(event) => setProgress(event.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
            />
          </label>
          <label className="text-sm font-semibold text-gray-700">
            Scheduled progress (0–1)
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={scheduled}
              onChange={(event) => setScheduled(event.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
            />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={submitSnapshot}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={submitting}
          >
            {submitting ? "Submitting..." : "Submit Snapshot"}
          </button>
          <button
            type="button"
            onClick={loadDelays}
            className="rounded-md border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-60"
            disabled={loadingDelays}
          >
            {loadingDelays ? "Loading..." : "Load Delays"}
          </button>
        </div>
        {status && <p className="text-xs text-emerald-600">{status}</p>}
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>

      <section className="rounded-xl border border-gray-200 bg-gray-50 p-5">
        <h3 className="text-lg font-semibold text-gray-900">Delayed snapshots</h3>
        {delays.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No delays loaded yet.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-gray-700">
            {delays.map((delay, idx) => (
              <li key={`${delay.timestamp ?? "delay"}-${idx}`} className="rounded border border-gray-200 bg-white p-3">
                <p className="font-semibold text-gray-900">{delay.location || location}</p>
                <p>{`Date: ${delay.timestamp || "Unknown"}`}</p>
                <p>{`Progress: ${delay.progress ?? "N/A"}`}</p>
                <p>{`Scheduled: ${delay.scheduled_progress ?? "N/A"}`}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
