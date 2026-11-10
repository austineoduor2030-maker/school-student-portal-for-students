import { useState } from "react";
import { api, useFetch } from "../../api";
import { useAuth } from "../../auth";
import { Banner, Loading, PageHead } from "../../components/ui";

const ROLES = [["student", "Student"], ["lecturer", "Lecturer"], ["hod", "Head of Department"], ["staff", "ICT / Registry"]];

export default function Users() {
  const { user: me } = useAuth();
  const st = useFetch("/staff/users/");
  const [error, setError] = useState("");

  async function patch(u, body) {
    setError("");
    try {
      await api(`/staff/users/${u.id}/`, { method: "PATCH", body });
      st.reload();
    } catch (e) {
      setError(e.message);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead title="Users & roles" sub="Change what a person can do, or switch an account off. Every change is logged. New accounts are created in the admin site." />
      <Banner>{error}</Banner>
      <div className="tw">
        <table>
          <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Access</th></tr></thead>
          <tbody>
            {st.data.map((u) => (
              <tr key={u.id}>
                <td><b>{u.name}</b><div className="note">{u.department || u.reg_no || ""}</div></td>
                <td>{u.username}</td>
                <td>
                  <select value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })}>
                    {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </td>
                <td>
                  <button className="sm" disabled={u.id === me.id} onClick={() => patch(u, { is_active: !u.is_active })}>
                    {u.is_active ? "Active · switch off" : "Off · switch on"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
