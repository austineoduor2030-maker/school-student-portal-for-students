import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Loading, Stat, money } from "../../components/ui";

export default function Dashboard() {
  const st = useFetch("/student/dashboard/");
  const units = useFetch("/student/units/");
  const [q, setQ] = useState("");
  const [reply, setReply] = useState(null);
  const [err, setErr] = useState("");

  async function ask(e) {
    e.preventDefault();
    if (!q.trim()) return;
    setErr("");
    try {
      setReply(await api("/student/ask/", { method: "POST", body: { question: q } }));
    } catch (x) {
      setErr(x.message);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  const d = st.data;
  const registered = ((units.data && units.data.units) || []).filter((u) => u.registration_id);
  const problems = d.attention.filter((a) => a.level !== "green");
  const good = d.attention.filter((a) => a.level === "green");

  return (
    <>
      {/* AI assistant: main top section, with notifications inside */}
      <div className="card">
        <h2>Ask your advisor</h2>
        <form className="row" style={{ flexWrap: "nowrap" }} onSubmit={ask}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Can I register for CIT 305?" />
          <button className="btn">Ask</button>
        </form>
        <Banner>{err}</Banner>
        {reply && (
          <p style={{ margin: "10px 0 0" }}>
            {reply.answer}
            {reply.citations.length > 0 && <span className="note"> Rules cited: {reply.citations.join(", ")}</span>}
          </p>
        )}
        <p className="note">For longer questions open <Link className="link" to="/student/advisor">Ask advisor</Link>.</p>

        <h2 style={{ marginTop: 14 }}>Notifications</h2>
        {problems.length === 0 && good.length === 0 && <p className="mu">Nothing needs your attention.</p>}
        {problems.map((a) => (
          <Link key={a.code + a.text} to={a.link} className="notice">{a.text}</Link>
        ))}
        {good.map((a) => (
          <Link key={a.code} to={a.link} className="notice ok">{a.text}</Link>
        ))}
      </div>

      {/* Four status cards */}
      <div className="grid">
        <Stat label="Credits" value={`${d.credits} / ${d.required_credits}`} bar={d.progress_percent} />
        <Stat label="GPA" value={d.gpa ?? "n/a"} />
        <Stat label="Fee balance" value={d.fees_balance > 0 ? money(d.fees_balance) : "Cleared"} />
        <Stat label="Registered this semester" value={`${d.registered_credits} credits`} />
      </div>

      <div className="two-col">
        {/* Explanation: bottom-left */}
        <div className="card">
          <h2>How your status is decided</h2>
          <div className="legend">
            <div><span className="pill g">Complete</span> <span className="note">All required data is captured.</span></div>
            <div><span className="pill a">Pending</span> <span className="note">Something is missing, but a valid reason was approved.</span></div>
            <div><span className="pill r">Blocked</span> <span className="note">Something is missing or wrong. Fix it before you can continue.</span></div>
          </div>
          <p className="note">Every answer cites the rule it used. Exceptions are decided by your HOD, not by the assistant.</p>
        </div>

        {/* Registered units: bottom-right */}
        <div className="card">
          <h2>Registered units</h2>
          {units.loading && <p className="mu">Loading…</p>}
          {!units.loading && registered.length === 0 && (
            <p className="mu">No units registered yet. <Link className="link" to="/student/register">Register units</Link></p>
          )}
          {registered.map((u) => (
            <div className="unit-line" key={u.id}>
              <span><b>{u.code}</b> {u.title}</span>
              <span className="note">{u.credits} cr</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
