import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, getWorkspaceId } from "../lib/api";

const FOLDER_STORAGE_KEY = "gdrive_public_folder_id";

const extractFolderId = (input) => {
  const trimmed = input.trim();
  if (!trimmed) return "";
  const foldersIndex = trimmed.indexOf("/folders/");
  if (foldersIndex !== -1) {
    const after = trimmed.slice(foldersIndex + "/folders/".length);
    return after.split(/[/?#]/)[0];
  }
  const idMatch = trimmed.match(/[?&]id=([^&#]+)/);
  if (idMatch) {
    return idMatch[1];
  }
  return trimmed;
};

const readStoredFolderId = () => {
  try {
    return localStorage.getItem(FOLDER_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
};

export default function Files() {
  const [folderInput, setFolderInput] = useState(readStoredFolderId);
  const [folderId, setFolderId] = useState(readStoredFolderId);
  const [files, setFiles] = useState([]);
  const [nextPageToken, setNextPageToken] = useState(null);
  const [status, setStatus] = useState(null);
  const [hydrationStatus, setHydrationStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState(null);
  const [connectMessage, setConnectMessage] = useState(null);
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
      setError("Enter a folder link or ID to list files.");
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
      setError("Enter a folder link or ID to ingest.");
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
            Google Drive Folder URL (or ID)
          </label>
          <input
            id="folder-id"
            value={folderInput}
            onChange={(event) => {
              const nextInput = event.target.value;
              const extractedId = extractFolderId(nextInput);
              setFolderInput(nextInput);
              setFolderId(extractedId);
              try {
                localStorage.setItem(FOLDER_STORAGE_KEY, extractedId);
              } catch {
                // Ignore storage failures (private mode, etc.)
              }
            }}
            placeholder="https://drive.google.com/drive/folders/<ID>"
            className="mt-2 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
          />
          <p className="mt-2 text-xs text-gray-500">Demo mode reads only folders shared as "Anyone with the link".</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Listing..." : "List Files"}
          </button>
          <button
            type="button"
            onClick={handleIngest}
            className="rounded-md border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-60"
            disabled={ingesting}
          >
            {ingesting ? "Queueing..." : "Ingest Now"}
          </button>
          <button
            type="button"
            onClick={() =>
              setConnectMessage(
                "Google Sign-In (private Drive) is coming soon. For now, paste a public folder link.",
              )
            }
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            Connect Google Drive
          </button>
        </div>
        {connectMessage && <p className="text-xs text-gray-500">{connectMessage}</p>}
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
