import { useFetch } from "../../api";
import { Loading, PageHead } from "../../components/ui";

export default function Graduation() {
  const st = useFetch("/staff/graduation/");
  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead title="Graduation clearance" sub="Eligible students first. Anything blocking is listed with its rule code." />
      <div className="tw">
        <table>
          <thead><tr><th>Student</th><th>Credits</th><th>GPA</th><th>Status</th><th>What is blocking</th></tr></thead>
          <tbody>
            {st.data.map((s) => (
              <tr key={s.id}>
                <td><b>{s.name}</b><div className="note">{s.reg_no}</div></td>
                <td>{s.passed_credits} / {s.required_credits}<div className="bar"><i style={{ width: `${s.progress_percent}%` }} /></div></td>
                <td>{s.gpa ?? "n/a"}</td>
                <td><span className={`pill ${s.eligible ? "g" : "r"}`}>{s.eligible ? "Eligible" : "Not eligible"}</span></td>
                <td>
                  {s.issues.length === 0 ? "Nothing" : s.issues.map((i) => (
                    <div key={i.code} style={{ marginBottom: 4 }}>
                      <span className={`pill ${i.blocking ? "r" : "a"}`}>{i.code}</span> <span className="note">{i.message}</span>
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
