export default function MicButton({ projectId }) {
  const onPickAudio = async (e) => {
    const f = e.target.files?.[0];
    if (!f || !projectId) return;
    const form = new FormData();
    form.append("file", f);
    const res = await fetch(`/api/speech/${projectId}`, { method: "POST", body: form });
    const data = await res.json();
    alert(`Transcript: ${data.transcript}\nAnswer: ${data.answer}`);
  };

  return (
    <label className="px-3 py-1 border rounded cursor-pointer">
      🎤 Mic
      <input type="file" accept="audio/*" className="hidden" onChange={onPickAudio} />
    </label>
  );
}