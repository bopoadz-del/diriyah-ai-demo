export default function MessageActions({ msg, index, onRefresh }) {
  const action = async (type) => {
    if (type === "refresh" && onRefresh) return onRefresh();
    const response = await fetch(`/api/workspace/messages/${msg.id}/action`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: type }),
    });
    if (!response.ok) {
      throw new Error("Failed to record message action");
    }
  };

  return (
    <div className="flex gap-1 text-sm items-center">
      <button title="Copy" onClick={() => action("copy")}>Copy</button>
      <button title="Like" onClick={() => action("like")}>Like</button>
      <button title="Dislike" onClick={() => action("dislike")}>Dislike</button>
      <button title="Mark as read" onClick={() => action("read")}>Read</button>
      <button title="Refresh" onClick={() => action("refresh")}>Refresh</button>
      <button title="Share" onClick={() => action("share")}>Share</button>
    </div>
  );
}