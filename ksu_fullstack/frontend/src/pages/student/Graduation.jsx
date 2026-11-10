import { useFetch } from "../../api";
import { Loading, PageHead } from "../../components/ui";

export default function Graduation() {
  const st = useFetch("/student/graduation/");
  if (st.loading || st.error) return <Loading state={st} />;
  const g = st.data;
  return (
    <>
      <PageHead title="Graduation check" sub="Every requirement is checked against your captured records." />
      <div className="card">
        <div className="row">
          <b>{g.passed_credits} of {g.required_credits} credits</b>
          <span className={`pill ${g.eligible ? "g" : "r"}`}>{g.eligible ? "Eligible" : "Not yet eligible"}</span>
        </div>
        <div className={`bar${g.eligible ? " g" : ""}`}><i style={{ width: `${g.progress_percent}%` }} /></div>
        <div className="note">GPA {g.gpa ?? "n/a"}</div>
      </div>
      <div className="card">
        <h2>Requirements</h2>
        {g.issues.length === 0 && <div className="check"><span className="tick g">✓</span><span>All requirements met.</span></div>}
        {g.issues.map((i) => (
          <div className="check" key={i.code}>
            <span className={`tick ${i.blocking ? "r" : "a"}`}>{i.blocking ? "!" : "~"}</span>
            <div>
              <b>{i.code}</b>
              <div className="note" style={{ fontSize: 13 }}>{i.message}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
