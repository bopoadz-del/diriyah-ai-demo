import React, { useState } from "react";
import { apiFetch, getWorkspaceId } from "../lib/api";

export default function Files() {
  const [folderId, setFolderId] = useState(readStoredFolderId);
  const [files, setFiles] = useState([]);
  const [nextPageToken, setNextPageToken] = useState(null);
  const [status, setStatus] = useState(null);
  const [hydrationStatus, setHydrationStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState(null);
  const workspaceId = getWorkspaceId();

  const workspaceId = useMemo(() => getWorkspaceId(), []);

  useEffect(() => {
    try {
      localStorage.setItem(FOLDER_STORAGE_KEY, folderId);
    } catch {
      // Ignore storage failures (private mode, etc.)
    }
  }, [folderId]);

  const handleList = async (event) => {
    event.preventDefault();
    setError(null);
    setStatus(null);
    setHydrationStatus(null);
    setFiles([]);
    setNextPageToken(null);

    const trimmedFolderId = folderId.trim();
    if (!trimmedFolderId) {
      setError("Enter a folder ID to list files.");
      return;
    }

    setLoading(true);
    try {
      const response = await apiFetch(`/api/drive/public/list?folder_id=${encodeURIComponent(trimmedFolderId)}`);
      if (!response.ok) {
        throw new Error(`Failed to list files (${response.status})`);
      }
      const data = await response.json();
      setFiles(data.files ?? []);
      setNextPageToken(data.next_page_token ?? null);
      setStatus("ok");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async () => {
    setError(null);
    setHydrationStatus(null);

    const trimmedFolderId = folderId.trim();
    if (!trimmedFolderId) {
      setError("Enter a folder ID to ingest.");
      return;
    }

    setIngesting(true);
    try {
      const response = await apiFetch("/api/drive/public/ingest", {
        method: "POST",
        body: JSON.stringify({ workspace_id: workspaceId, dry_run: false }),
      });
      if (!response.ok) {
        throw new Error(`Failed to start ingestion (${response.status})`);
      }
      const data = await response.json();
      setHydrationStatus(`Hydration queued (job ${data.job_id ?? "unknown"}).`);
    } catch (err) {
      setError(err.message);
    } finally {
      setIngesting(false);
    }
  };

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#a67c52]">Files</p>
        <h2 className="text-2xl font-semibold text-gray-900">Public Google Drive</h2>
        <p className="text-sm text-gray-600">
          List files in a public Drive folder and trigger a hydration run for the active workspace{" "}
          <span className="font-semibold text-gray-900">{workspaceId}</span>.
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
            onClick={handleIngest}
            className="rounded-md border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-60"
            disabled={ingesting}
          >
            {ingesting ? "Queueing..." : "Ingest now"}
          </button>
        </div>
        {status && <p className="text-xs text-gray-500">Drive status: {status}</p>}
        {nextPageToken && (
          <p className="text-xs text-gray-500">More files available. Next page token: {nextPageToken}</p>
        )}
        {hydrationStatus && (
          <p className="text-sm text-emerald-700">
            {hydrationStatus} <Link to={`/hydration/${workspaceId}`}>View hydration status</Link>
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      <section className="rounded-xl border border-gray-200 bg-gray-50 p-5">
        <h3 className="text-lg font-semibold text-gray-900">Files</h3>
        {files.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No files loaded yet.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">MIME type</th>
                  <th className="pb-2 pr-4">Modified</th>
                  <th className="pb-2">Size</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {files.map((file) => (
                  <tr key={file.id} className="text-gray-700">
                    <td className="py-2 pr-4 font-medium text-gray-900">{file.name}</td>
                    <td className="py-2 pr-4">{file.mimeType || "-"}</td>
                    <td className="py-2 pr-4">
                      {file.modifiedTime ? new Date(file.modifiedTime).toLocaleString() : "-"}
                    </td>
                    <td className="py-2">{file.size ? `${file.size} bytes` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
