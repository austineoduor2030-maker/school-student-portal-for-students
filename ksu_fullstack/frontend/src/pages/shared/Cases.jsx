import { useState } from "react";
import { api, useFetch } from "../../api";
import { Banner, Empty, Loading, PageHead, Pill, when } from "../../components/ui";

/** Approvals queue for HOD and staff. Deciding is always a person's act. */
export default function Cases() {
  const [filter, setFilter] = useState("requested");
  const st = useFetch(`/cases/?status=${filter}`);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState("");

  async function decide(c, decision) {
    setError("");
    try {
      await api(`/cases/${c.id}/decide/`, { method: "POST", body: { decision, note: notes[c.id] || "" } });
      st.reload();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <PageHead title="Approvals" sub="Missing-mark reasons and prerequisite waivers waiting for a human decision." />
      <div className="row start" style={{ marginBottom: 12 }}>
        {["requested", "approved", "rejected"].map((s) => (
          <button key={s} className={`sm${filter === s ? " on" : ""}`} onClick={() => setFilter(s)}>
            {s === "requested" ? "Waiting" : s[0].toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>
      <Banner>{error}</Banner>
      {st.loading || st.error ? <Loading state={st} /> : st.data.length === 0 ? <Empty>Nothing here.</Empty> : (
        st.data.map((c) => (
          <div className="card" key={c.id}>
            <div className="row">
              <b>{c.kind_label}: {c.student.name} · {c.unit.code}</b>
              <Pill status={c.status} />
            </div>
            <div className="note">{c.student.reg_no} · raised by {c.requested_by} · {when(c.created_at)}</div>
            <p style={{ margin: "8px 0" }}>{c.reason}</p>
            {c.status === "requested" ? (
              <>
                <input placeholder="Note (required when rejecting)" value={notes[c.id] || ""} onChange={(e) => setNotes({ ...notes, [c.id]: e.target.value })} />
                <div className="row-actions" style={{ marginTop: 8 }}>
                  <button className="btn" onClick={() => decide(c, "approved")}>Approve</button>
                  <button className="btn danger" onClick={() => decide(c, "rejected")}>Reject</button>
                </div>
              </>
            ) : (
              <p className="note">Decided by {c.decided_by} on {when(c.decided_at)}{c.decision_note ? `: ${c.decision_note}` : ""}</p>
            )}
          </div>
        ))
      )}
    </>
  );
}
