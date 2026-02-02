import React, { useState } from "react";
import { apiFetch } from "../lib/api";

const WORKSPACE_ID = "demo";

export default function Files() {
  const [folderId, setFolderId] = useState("");
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState(null);
  const [hydrationStatus, setHydrationStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleList = async (event) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    setFiles([]);

    if (!folderId.trim()) {
      setError("Enter a folder ID to list files.");
      return;
    }

    setLoading(true);
    try {
      const response = await apiFetch(`/api/drive/public/list?folder_id=${encodeURIComponent(folderId.trim())}`);
      if (!response.ok) {
        throw new Error(`Failed to list files (${response.status})`);
      }
      const data = await response.json();
      setFiles(data.files ?? []);
      setStatus(data.status ?? "ok");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleHydration = async () => {
    setHydrationStatus(null);
    setError(null);
    try {
      const response = await apiFetch("/api/hydration/run-now", {
        method: "POST",
        body: JSON.stringify({ workspace_id: WORKSPACE_ID, dry_run: false }),
      });
      if (!response.ok) {
        throw new Error(`Failed to start hydration (${response.status})`);
      }
      const data = await response.json();
      setHydrationStatus(`Hydration queued (job ${data.job_id ?? "unknown"})`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Files</p>
        <h2 className="text-2xl font-semibold text-gray-900">Drive Public ingest</h2>
        <p className="text-sm text-gray-600">
          List files in a public Drive folder and trigger a hydration run for workspace {WORKSPACE_ID}.
        </p>
      </header>

      <form onSubmit={handleList} className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
        <div>
          <label htmlFor="folder-id" className="text-sm font-semibold text-gray-700">
            Public folder ID
          </label>
          <input
            id="folder-id"
            value={folderId}
            onChange={(event) => setFolderId(event.target.value)}
            placeholder="Enter Google Drive folder ID"
            className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Listing..." : "List files"}
          </button>
          <button
            type="button"
            onClick={handleHydration}
            className="rounded-md border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700"
          >
            Run hydration now
          </button>
        </div>
        {status && <p className="text-xs text-gray-500">Drive status: {status}</p>}
        {hydrationStatus && <p className="text-sm text-emerald-700">{hydrationStatus}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      <section className="rounded-xl border border-gray-200 bg-gray-50 p-5">
        <h3 className="text-lg font-semibold text-gray-900">Files</h3>
        {files.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No files loaded yet.</p>
        ) : (
          <div className="mt-3 space-y-3">
            {files.map((file) => (
              <article key={file.source_document_id} className="rounded-lg border border-gray-200 bg-white p-4">
                <p className="text-sm font-semibold text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500">{file.mime_type || "unknown type"}</p>
                {file.modified_time && (
                  <p className="text-xs text-gray-500">Modified: {new Date(file.modified_time).toLocaleString()}</p>
                )}
                {file.size_bytes && <p className="text-xs text-gray-500">Size: {file.size_bytes} bytes</p>}
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
