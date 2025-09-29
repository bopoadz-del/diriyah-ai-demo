import { useEffect, useState } from "react";

export default function Metrics() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetch("/api/analytics").then(r => r.json()).then(setLogs);
  }, []);

  const counts = logs.reduce((acc, l) => {
    acc[l.action] = (acc[l.action] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-4">
      <h1 className="font-bold text-lg mb-4">Metrics Dashboard</h1>
      <div className="mb-4 flex gap-4">
        {Object.entries(counts).map(([action, count]) => (
          <div key={action} className="border p-2 rounded">
            {action}: {count}
          </div>
        ))}
      </div>
      <table className="border w-full">
        <thead>
          <tr><th>Action</th><th>User</th><th>Message</th><th>Time</th></tr>
        </thead>
        <tbody>
          {logs.map(l => (
            <tr key={l.id}>
              <td>{l.action}</td>
              <td>{l.user_id}</td>
              <td>{l.message_id}</td>
              <td>{l.timestamp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}