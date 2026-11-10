import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { PageHead } from "../../components/ui";

const EXAMPLES = ["Can I register for CIT 305?", "Do I meet graduation requirements?", "Do I owe any fees?", "How are my results?"];

export default function Advisor() {
  const [log, setLog] = useState([
    { who: "bot", text: "Hi. I answer from your own records: registration, prerequisites, fees, results and graduation. Decisions like waivers stay with your HOD." },
  ]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => { if (end.current) end.current.scrollTop = end.current.scrollHeight; }, [log]);

  async function send(text) {
    const question = (text ?? q).trim();
    if (!question || busy) return;
    setQ("");
    setBusy(true);
    setLog((l) => [...l, { who: "me", text: question }]);
    try {
      const r = await api("/student/ask/", { method: "POST", body: { question } });
      setLog((l) => [...l, { who: "bot", text: r.answer, cites: r.citations, action: r.suggested_action, escalate: r.escalate }]);
    } catch (e) {
      setLog((l) => [...l, { who: "sys", text: e.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead title="Ask advisor" sub="Answers cite the rule they used. If I am unsure, I send you to a person." />
      <div className="chat" ref={end}>
        {log.map((m, i) => (
          <div key={i} className={`msg ${m.who}`}>
            {m.text}
            {m.cites && m.cites.length > 0 && <span className="src">Rules cited: {m.cites.join(", ")}</span>}
            {m.action && (
              <div style={{ marginTop: 8 }}>
                <Link className="sm" to={`/student/requests?unit=${m.action.unit_id}`}>{m.action.label}</Link>
              </div>
            )}
            {m.escalate && <span className="src">This is outside your records. Please see your HOD or the registry.</span>}
          </div>
        ))}
        {busy && <div className="msg bot mu">Checking your records…</div>}
      </div>
      <div className="row start" style={{ marginBottom: 10 }}>
        {EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => send(e)}>{e}</button>)}
      </div>
      <form className="row" style={{ flexWrap: "nowrap" }} onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type your question" maxLength={500} />
        <button className="btn" disabled={busy || !q.trim()}>Send</button>
      </form>
    </>
  );
}
