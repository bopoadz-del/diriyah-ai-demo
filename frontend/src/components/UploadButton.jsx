import { useState } from "react";
import { apiFetch } from "../lib/api";

export default function UploadButton({ projectId, driveFolderId, chatId }) {
  const [statusMessage, setStatusMessage] = useState(null);
  const [classification, setClassification] = useState(null);
  const [actionItems, setActionItems] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const onPickDoc = async (e) => {
    const f = e.target.files?.[0];
    if (!f || !projectId) return;
    setStatusMessage(null);
    setClassification(null);
    setActionItems([]);
    setErrorMessage(null);
    setIsProcessing(true);
    const form = new FormData();
    form.append("file", f);
    const qs = new URLSearchParams();
    if (chatId) qs.set("chat_id", String(chatId));
    if (driveFolderId) qs.set("drive_folder_id", String(driveFolderId));
    try {
      const res = await apiFetch(`/api/upload/${projectId}?${qs.toString()}`, {
        method: "POST",
        body: form
      });
      if (!res.ok) {
        throw new Error("Upload failed.");
      }
      const data = await res.json();
      setStatusMessage(`Uploaded, indexed${data.summarized ? " and summarized" : ""}!`);

      const text = await f.text();
      const classifyRes = await apiFetch("/api/document_classifier/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!classifyRes.ok) {
        throw new Error("Document classification failed.");
      }
      const classifyData = await classifyRes.json();
      setClassification({
        type: classifyData.type,
        confidence: classifyData.confidence,
      });

      if (classifyData.type === "Meeting Minutes") {
        const extractRes = await apiFetch("/api/action_item_extractor/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (!extractRes.ok) {
          throw new Error("Action item extraction failed.");
        }
        const extractedItems = await extractRes.json();
        const normalizedItems = Array.isArray(extractedItems)
          ? extractedItems
          : extractedItems.action_items || extractedItems.items || [];
        setActionItems(normalizedItems);
      }
    } catch (error) {
      setErrorMessage(error.message ?? "Something went wrong during upload.");
    } finally {
      setIsProcessing(false);
      e.target.value = "";
    }
  };

  return (
    <div className="space-y-3">
      <label className="inline-flex items-center gap-2 px-3 py-1 border rounded cursor-pointer">
        <span>{isProcessing ? "Processing..." : "Upload document"}</span>
        <input type="file" className="hidden" onChange={onPickDoc} />
      </label>
      {statusMessage && <p className="text-xs text-emerald-600">{statusMessage}</p>}
      {errorMessage && <p className="text-xs text-red-600">{errorMessage}</p>}
      {classification && (
        <div className="rounded border border-slate-200 bg-white p-3 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">Detected type</p>
          <p>
            {classification.type} (confidence{" "}
            {typeof classification.confidence === "number"
              ? `${(classification.confidence * 100).toFixed(1)}%`
              : "N/A"}
            )
          </p>
        </div>
      )}
      {actionItems.length > 0 && (
        <div className="rounded border border-slate-200 bg-white p-3 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">Action items</p>
          <ul className="mt-2 space-y-2">
            {actionItems.map((item, index) => (
              <li key={`${item.description ?? "action"}-${index}`} className="rounded border border-slate-100 p-2">
                <p className="font-medium text-slate-900">{item.description ?? "Action item"}</p>
                <p>Assignee: {item.assignee || "Unassigned"}</p>
                <p>Due: {item.due_date || item.dueDate || "Not set"}</p>
                <p>Priority: {item.priority || "Normal"}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
