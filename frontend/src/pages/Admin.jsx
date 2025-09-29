import { useEffect, useState } from "react";

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    fetch("/api/users").then(r => r.json()).then(setUsers);
  }, []);

  const addUser = async () => {
    const res = await fetch("/api/users", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({name, email})
    });
    const u = await res.json();
    setUsers(prev => [...prev, u]);
    setName(""); setEmail("");
  };

  return (
    <div className="p-4">
      <h1 className="font-bold text-lg mb-4">User Management</h1>
      <div className="mb-4">
        <input className="border p-1 mr-2" value={name} onChange={e=>setName(e.target.value)} placeholder="Name"/>
        <input className="border p-1 mr-2" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email"/>
        <button className="border px-3 py-1" onClick={addUser}>Add</button>
      </div>
      <ul>
        {users.map(u => (
          <li key={u.id}>{u.name} ({u.email}) — {u.role}</li>
        ))}
      </ul>
    </div>
  );
}