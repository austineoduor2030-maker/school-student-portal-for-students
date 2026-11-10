import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Loading, PageHead, Pill, money } from "../../components/ui";

export default function Students() {
  const st = useFetch("/staff/students/");
  const [edit, setEdit] = useState(null); // {id, value}
  const [error, setError] = useState("");

  async function saveFees() {
    setError("");
    try {
      await api(`/staff/students/${edit.id}/fees/`, { method: "PUT", body: { fees_balance: edit.value } });
      setEdit(null);
      st.reload();
    } catch (e) {
      setError(e.message);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead title="Students & transcripts" sub="Update fee balances and release transcripts. Release is refused while any mark is blocked." />
      <Banner>{error}</Banner>
      <div className="tw">
        <table>
          <thead><tr><th>Student</th><th>Year</th><th>GPA</th><th>Credits</th><th>Fee balance</th><th>Transcript</th></tr></thead>
          <tbody>
            {st.data.map((s) => (
              <tr key={s.id}>
                <td><b>{s.name}</b><div className="note">{s.reg_no}</div></td>
                <td>{s.year}</td>
                <td>{s.gpa ?? "n/a"}</td>
                <td>{s.credits}</td>
                <td>
                  {edit && edit.id === s.id ? (
                    <div className="row-actions">
                      <input className="num" inputMode="decimal" value={edit.value} onChange={(e) => setEdit({ ...edit, value: e.target.value })} />
                      <button className="sm" onClick={saveFees}>Save</button>
                      <button className="sm" onClick={() => setEdit(null)}>Cancel</button>
                    </div>
                  ) : (
                    <>
                      {s.fees_balance > 0 ? <Pill cls="r">{money(s.fees_balance)}</Pill> : <Pill cls="g">Cleared</Pill>}{" "}
                      <button className="sm" onClick={() => setEdit({ id: s.id, value: String(s.fees_balance) })}>Edit</button>
                    </>
                  )}
                </td>
                <td>
                  <Link className="sm" to={`/staff/students/${s.id}/transcript`}>
                    {s.transcript_ready ? "Open" : "Open (blocked)"}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
