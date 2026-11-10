import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Loading, PageHead, Pill } from "../../components/ui";

export default function Transcript() {
  const { id } = useParams();
  const st = useFetch(`/staff/students/${id}/transcript/`);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  async function release() {
    setError("");
    setOk("");
    try {
      await api(`/staff/students/${id}/transcript/release/`, { method: "POST" });
      setOk("Transcript released and logged.");
    } catch (e) {
      setError(e.message);
      st.reload();
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  const t = st.data;
  const r = t.readiness;
  return (
    <>
      <p className="note"><Link className="link" to="/staff/students">← Back to students</Link></p>
      <PageHead title={`Transcript: ${t.student.name}`} sub={`${t.student.reg_no} · ${t.student.program} · GPA ${t.gpa ?? "n/a"} · ${t.credits} credits`} />
      <Banner>{error}</Banner>
      <Banner kind="g">{ok}</Banner>
      {r.ready ? (
        <div className="box g">
          Ready to release.{r.pending_units.length > 0 && ` Units shown as “results pending”: ${r.pending_units.join(", ")}.`}
        </div>
      ) : (
        <div className="box r">Cannot release: marks missing for {r.blocked_units.join(", ")}.</div>
      )}
      <div className="tw">
        <table>
          <thead><tr><th>Year</th><th>Unit</th><th>Total</th><th>Grade</th><th>Status</th></tr></thead>
          <tbody>
            {t.rows.map((m) => (
              <tr key={m.id}>
                <td>{m.academic_year}</td>
                <td>{m.unit.code} · {m.unit.title}</td>
                <td>{m.total ?? "–"}</td>
                <td>{m.status === "pending" ? "Results pending" : m.grade ?? "–"}</td>
                <td><Pill status={m.status} />{m.status !== "complete" && <div className="note">{m.note}</div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="btn" disabled={!r.ready} onClick={release}>Release transcript</button>
    </>
  );
}
