import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useFetch } from "../../api";
import { Banner, Issues, Loading, PageHead, Pill } from "../../components/ui";

export default function Register() {
  const st = useFetch("/student/units/");
  const [busy, setBusy] = useState(null);
  const [problem, setProblem] = useState(null); // {message, issues}
  const [done, setDone] = useState("");

  async function act(unit, drop) {
    setBusy(unit.id);
    setProblem(null);
    setDone("");
    try {
      if (drop) await api(`/student/registrations/${unit.registration_id}/`, { method: "DELETE" });
      else await api("/student/registrations/", { method: "POST", body: { unit_id: unit.id } });
      setDone(drop ? `${unit.code} dropped.` : `${unit.code} registered.`);
      st.reload();
    } catch (e) {
      // The server is the authority: if it refuses, show exactly why.
      setProblem({ message: e.message, issues: e.issues });
    } finally {
      setBusy(null);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  const { units, profile_issues, max_credits } = st.data;
  const registered = units.filter((u) => u.registration_id);
  const credits = registered.reduce((s, u) => s + u.credits, 0);

  return (
    <>
      <PageHead title="Register units" sub={`Maximum ${max_credits} credits per semester. The system checks every rule before it lets you submit.`} />

      {profile_issues.length > 0 && (
        <div className="box a">
          <div className="row">
            <span>{profile_issues[0].message}</span>
            <Link className="pill a" to="/student/profile">Complete profile</Link>
          </div>
        </div>
      )}
      <Banner>{problem && problem.message}</Banner>
      {problem && <Issues issues={problem.issues} />}
      <Banner kind="g">{done}</Banner>

      {units.length === 0 && <p className="mu">No units are open to you this semester.</p>}
      {units.map((u) => (
        <div key={u.id} className={`card unit${u.eligible || u.registration_id ? "" : " blocked"}`}>
          <div style={{ flex: 1 }}>
            <b>{u.code} · {u.title}</b>
            <div className="note">
              {u.credits} credits · Year {u.year} Sem {u.semester}
              {u.prerequisites.length > 0 && ` · Needs ${u.prerequisites.join(", ")}`}
            </div>
            {u.registration_id ? (
              <div style={{ marginTop: 6 }}><Pill cls="g">Registered</Pill></div>
            ) : (
              <>
                <Issues issues={u.issues} />
                {u.issues.some((i) => i.code === "PREREQ_MISSING") && (
                  <div style={{ marginTop: 8 }}>
                    {u.waiver ? (
                      <Pill status={u.waiver.status}>Waiver: {u.waiver.status}</Pill>
                    ) : (
                      <Link className="sm" to={`/student/requests?unit=${u.id}`}>Ask HOD for a waiver</Link>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          {u.registration_id ? (
            <button className="sm" disabled={busy === u.id} onClick={() => act(u, true)}>Drop</button>
          ) : (
            <button className="btn" disabled={!u.eligible || busy === u.id || profile_issues.length > 0} onClick={() => act(u, false)}>
              Register
            </button>
          )}
        </div>
      ))}
      <p className="note">Registered so far: {credits} credits.</p>
    </>
  );
}
