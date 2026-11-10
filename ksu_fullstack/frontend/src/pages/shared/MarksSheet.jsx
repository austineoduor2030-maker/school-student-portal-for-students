import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Loading, PageHead, Pill } from "../../components/ui";

/** The marks gate in one screen. Server decides each row's status; this page only shows it. */
export default function MarksSheet({ base }) {
  const { unitId } = useParams();
  const st = useFetch(`/marks/units/${unitId}/roster/`);
  const [rows, setRows] = useState([]);
  const [drafts, setDrafts] = useState({}); // student id -> {cat, exam, on_score_sheet}
  const [msg, setMsg] = useState({});       // student id -> {kind, text}
  const [askFor, setAskFor] = useState(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!st.data) return;
    setRows(st.data.rows);
    setDrafts({});
  }, [st.data]);

  const val = (r, k) => {
    const d = drafts[r.student.id];
    return d && k in d ? d[k] : k === "on_score_sheet" ? r.on_score_sheet : r[k] ?? "";
  };
  const edit = (r, k, v) => setDrafts((d) => ({ ...d, [r.student.id]: { ...d[r.student.id], [k]: v } }));
  const say = (r, kind, text) => setMsg((m) => ({ ...m, [r.student.id]: { kind, text } }));
  const replace = (row) => setRows((rs) => rs.map((x) => (x.student.id === row.student.id ? row : x)));

  async function save(r) {
    try {
      const row = await api("/marks/", {
        method: "PUT",
        body: { unit_id: Number(unitId), student_id: r.student.id, cat: val(r, "cat"), exam: val(r, "exam"), on_score_sheet: !!val(r, "on_score_sheet") },
      });
      replace(row);
      setDrafts((d) => { const n = { ...d }; delete n[r.student.id]; return n; });
      say(r, "g", "Saved.");
    } catch (e) {
      say(r, "r", e.message);
    }
  }

  async function ask(r) {
    try {
      await api("/marks/exceptions/", { method: "POST", body: { unit_id: Number(unitId), student_id: r.student.id, reason } });
      setAskFor(null);
      setReason("");
      say(r, "g", "Request sent to the HOD / staff.");
      st.reload();
    } catch (e) {
      say(r, "r", e.message);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  const { unit, limits } = st.data;
  const blocked = rows.filter((r) => r.status === "blocked");

  return (
    <>
      <p className="note"><Link className="link" to={base === "/lecturer" ? "/lecturer" : "/staff/marks"}>← Back to units</Link></p>
      <PageHead title={`${unit.code} · ${unit.title}`} sub={`CAT out of ${limits.cat_max}, exam out of ${limits.exam_max}. Leave a box empty only if the mark truly does not exist.`} />

      {blocked.length === 0 ? (
        <div className="box g">Every mark is complete or has an approved reason. This sheet can go forward.</div>
      ) : (
        <div className="box r">Blocked: {blocked.map((r) => r.student.reg_no).join(", ")}. Capture the marks or request an exception with a valid reason.</div>
      )}

      <div className="tw">
        <table>
          <thead>
            <tr><th>Student</th><th>CAT</th><th>Exam</th><th>On score sheet?</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan="6" className="empty">No students registered for this unit.</td></tr>}
            {rows.map((r) => {
              const m = msg[r.student.id];
              const dirty = !!drafts[r.student.id];
              const canAsk = r.status === "blocked" && !r.on_score_sheet && !(r.request && r.request.status === "requested");
              return (
                <tr key={r.student.id}>
                  <td><b>{r.student.name}</b><div className="note">{r.student.reg_no}</div></td>
                  <td><input className="num" inputMode="decimal" value={val(r, "cat")} onChange={(e) => edit(r, "cat", e.target.value)} /></td>
                  <td><input className="num" inputMode="decimal" value={val(r, "exam")} onChange={(e) => edit(r, "exam", e.target.value)} /></td>
                  <td>
                    <label style={{ margin: 0, display: "flex", gap: 6, alignItems: "center" }}>
                      <input type="checkbox" checked={!!val(r, "on_score_sheet")} onChange={(e) => edit(r, "on_score_sheet", e.target.checked)} />
                      value exists
                    </label>
                  </td>
                  <td>
                    <Pill status={r.status} />
                    {r.status !== "complete" && <div className="note">{r.note}</div>}
                    {r.request && <div className="note">Request: {r.request.status}</div>}
                    {m && <div className={`note ${m.kind === "r" ? "err-text" : "ok-text"}`}>{m.text}</div>}
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="btn" style={{ padding: "6px 12px" }} disabled={!dirty} onClick={() => save(r)}>Save</button>
                      {canAsk && <button className="sm" onClick={() => { setAskFor(r.student.id); setReason(""); }}>Request exception</button>}
                    </div>
                    {askFor === r.student.id && (
                      <div style={{ marginTop: 8 }}>
                        <textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Valid reason: deferral, medical, special consideration…" />
                        <div className="row-actions" style={{ marginTop: 6 }}>
                          <button className="sm" disabled={reason.trim().length < 10} onClick={() => ask(r)}>Send</button>
                          <button className="sm" onClick={() => setAskFor(null)}>Cancel</button>
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Banner kind="g">{""}</Banner>
      <p className="note">
        An exception only turns a missing mark into <b>pending</b> after the HOD or staff approve it. If the value is on the
        score sheet, tick “value exists” and capture it: a reason cannot excuse data that is available.
      </p>
    </>
  );
}
