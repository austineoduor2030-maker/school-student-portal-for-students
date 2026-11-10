import { Link } from "react-router-dom";
import { useFetch } from "../../api";
import { Empty, Loading, PageHead, Stat } from "../../components/ui";

export default function Dashboard() {
  const st = useFetch("/hod/dashboard/");
  if (st.loading || st.error) return <Loading state={st} />;
  const d = st.data;
  return (
    <>
      <PageHead title="Department overview" sub={d.department || "All departments"} />
      <div className="grid">
        <Stat label="Students" value={d.students} />
        <Stat label="Waiting for your decision" value={d.open_cases} />
        <Stat label="Blocked marks" value={d.blocked_marks} />
        <Stat label="Pending (approved reason)" value={d.pending_marks} />
      </div>
      {d.open_cases > 0 && (
        <Link to="/hod/cases" className="box a" style={{ display: "block" }}>
          <div className="row"><span>{d.open_cases} request(s) need a decision.</span><span className="pill a">Review</span></div>
        </Link>
      )}
      <h2 style={{ marginTop: 16 }}>Students at risk</h2>
      {d.at_risk.length === 0 ? <Empty>No students flagged.</Empty> : (
        <div className="tw">
          <table>
            <thead><tr><th>Student</th><th>Year</th><th>Why flagged</th></tr></thead>
            <tbody>
              {d.at_risk.map((s) => (
                <tr key={s.id}>
                  <td><b>{s.name}</b><div className="note">{s.reg_no}</div></td>
                  <td>{s.year}</td>
                  <td>{s.reasons.map((r) => <span key={r} className="pill r" style={{ marginRight: 4 }}>{r}</span>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
