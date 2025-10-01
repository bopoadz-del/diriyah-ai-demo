import { useEffect, useMemo, useState } from "react";

const USERS_ENDPOINT = "/api/users/me";
const UPDATE_ENDPOINT = "/api/users/update";

export default function Admin() {
  const [user, setUser] = useState(null);
  const [formState, setFormState] = useState({ name: "", role: "", projects: "" });
  const [ack, setAck] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const response = await fetch(USERS_ENDPOINT);
        if (!response.ok) {
          throw new Error(`Failed to load user (status ${response.status})`);
        }
        const data = await response.json();
        setUser(data);
        setFormState({
          name: data.name ?? "",
          role: data.role ?? "",
          projects: Array.isArray(data.projects) ? data.projects.join(", ") : "",
        });
        setError(null);
      } catch (err) {
        console.error(err);
        setError("Unable to load user information.");
      }
    };

    loadUser();
  }, []);

  const updateUser = async () => {
    if (!user) {
      return;
    }

    const projectIds = formState.projects
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean)
      .map((p) => Number(p))
      .filter((p) => !Number.isNaN(p));

    try {
      const response = await fetch(UPDATE_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: user.id,
          name: formState.name,
          role: formState.role,
          projects: projectIds,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.message || "Failed to update user");
      }

      setAck(payload);
      setError(null);
      setUser((prev) =>
        prev
          ? {
              ...prev,
              name: formState.name,
              role: formState.role,
              projects: projectIds,
            }
          : prev,
      );
    } catch (err) {
      console.error(err);
      setError("Update failed. Please try again.");
      setAck(null);
    }
  };

  const projectsList = useMemo(() => {
    if (!user?.projects?.length) {
      return "None";
    }
    return user.projects.join(", ");
  }, [user]);

  return (
    <div className="p-4 space-y-4">
      <h1 className="font-bold text-lg">User Management</h1>

      {error && <p className="text-red-600">{error}</p>}

      {user ? (
        <div className="space-y-2">
          <div>
            <p><span className="font-semibold">User ID:</span> {user.id}</p>
            <p><span className="font-semibold">Name:</span> {user.name}</p>
            <p><span className="font-semibold">Role:</span> {user.role}</p>
            <p><span className="font-semibold">Projects:</span> {projectsList}</p>
          </div>

          <div className="space-y-2">
            <h2 className="font-semibold">Update User (stub)</h2>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                className="border p-2 flex-1"
                value={formState.name}
                onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Name"
              />
              <input
                className="border p-2 flex-1"
                value={formState.role}
                onChange={(event) => setFormState((prev) => ({ ...prev, role: event.target.value }))}
                placeholder="Role"
              />
              <input
                className="border p-2 flex-1"
                value={formState.projects}
                onChange={(event) => setFormState((prev) => ({ ...prev, projects: event.target.value }))}
                placeholder="Projects (comma separated IDs)"
              />
              <button className="border px-4 py-2" onClick={updateUser}>
                Save
              </button>
            </div>
          </div>

          {ack && (
            <p className="text-green-600">
              {ack.status === "ok" ? ack.message : ack.status}
            </p>
          )}
        </div>
      ) : (
        <p>Loading user…</p>
      )}
    </div>
  );
}
