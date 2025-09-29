export default function MessageActions({ msg, index, onRefresh }) {
  const action = async (type) => {
    if (type === "refresh" && onRefresh) return onRefresh();
    await fetch(`/api/messages/${msg.id}/action?action=${type}`, { method: "PUT" });
  };

  return (
    <div className="flex gap-1 text-sm items-center">
      <button title="Copy" onClick={() => action("copy")}>📋</button>
      <button title="Like" onClick={() => action("like")}>👍</button>
      <button title="Dislike" onClick={() => action("dislike")}>👎</button>
      <button title="Read" onClick={() => action("read")}>👁️</button>
      <button title="Refresh" onClick={() => action("refresh")}>🔄</button>
      <button title="Share" onClick={() => action("share")}>🔗</button>
    </div>
  );
}