import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Empty, Loading, PageHead, Pill, when } from "../../components/ui";

export default function Requests() {
  const list = useFetch("/student/requests/");
  const units = useFetch("/student/units/");
  const [params] = useSearchParams();
  const [unitId, setUnitId] = useState(params.get("unit") || "");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (params.get("unit")) setUnitId(params.get("unit")); }, [params]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setOk("");
    setBusy(true);
    try {
      await api("/student/requests/", { method: "POST", body: { unit_id: Number(unitId), reason } });
      setOk("Request sent. The HOD or registry will decide; you will see the outcome here.");
      setReason("");
      list.reload();
      units.reload();
    } catch (x) {
      setError(x.message);
    } finally {
      setBusy(false);
    }
  }

  const needing = units.data ? units.data.units.filter((u) => u.issues.some((i) => i.code === "PREREQ_MISSING") && !u.waiver) : [];

  return (
    <>
      <PageHead title="My requests" sub="Prerequisite waivers are decided by people, not by the system." />
      <form className="card" onSubmit={submit}>
        <h2>Ask for a prerequisite waiver</h2>
        <Banner>{error}</Banner>
        <Banner kind="g">{ok}</Banner>
        <label htmlFor="unit">Unit</label>
        <select id="unit" value={unitId} onChange={(e) => setUnitId(e.target.value)}>
          <option value="">Choose a unit</option>
          {needing.map((u) => <option key={u.id} value={u.id}>{u.code} · {u.title}</option>)}
          {unitId && !needing.some((u) => String(u.id) === String(unitId)) && units.data && (
            <option value={unitId}>
              {(units.data.units.find((u) => String(u.id) === String(unitId)) || { code: "Selected unit" }).code}
            </option>
          )}
        </select>
        <label htmlFor="why">Why should it be waived?</label>
        <textarea id="why" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. I completed the equivalent unit at another institution." />
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy || !unitId || reason.trim().length < 10}>Send request</button>
        </div>
      </form>

      <h2>History</h2>
      {list.loading || list.error ? <Loading state={list} /> : list.data.length === 0 ? <Empty>No requests yet.</Empty> : (
        list.data.map((r) => (
          <div className="card" key={r.id}>
            <div className="row">
              <b>{r.unit.code} · {r.kind_label}</b>
              <Pill status={r.status} />
            </div>
            <div className="note">{when(r.created_at)}</div>
            <p style={{ margin: "6px 0 0" }}>{r.reason}</p>
            {r.decision_note && <p className="note">Decision by {r.decided_by}: {r.decision_note}</p>}
          </div>
        ))
      )}
    </>
  );
}
