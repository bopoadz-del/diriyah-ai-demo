export default function CamButton({ projectId }) {
  const onPickImage = async (e) => {
    const f = e.target.files?.[0];
    if (!f || !projectId) return;
    const form = new FormData();
    form.append("file", f);
    const res = await fetch(`/api/vision/${projectId}`, { method: "POST", body: form });
    const data = await res.json();
    alert(`YOLO Summary: ${data.summary}`);
  };

  return (
    <label className="px-3 py-1 border rounded cursor-pointer">
      📷 Cam
      <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onPickImage} />
    </label>
  );
}