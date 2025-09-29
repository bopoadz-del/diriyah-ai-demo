export default function UploadButton({ projectId, driveFolderId, chatId }) {
  const onPickDoc = async (e) => {
    const f = e.target.files?.[0];
    if (!f || !projectId) return;
    const form = new FormData();
    form.append("file", f);
    const qs = new URLSearchParams();
    if (chatId) qs.set("chat_id", String(chatId));
    if (driveFolderId) qs.set("drive_folder_id", String(driveFolderId));
    const res = await fetch(`/api/upload/${projectId}?${qs.toString()}`, {
      method: "POST",
      body: form
    });
    const data = await res.json();
    alert(`Uploaded, indexed${data.summarized ? " and summarized" : ""}!`);
  };

  return (
    <label className="px-3 py-1 border rounded cursor-pointer">
      📎 Upload
      <input type="file" className="hidden" onChange={onPickDoc} />
    </label>
  );
}