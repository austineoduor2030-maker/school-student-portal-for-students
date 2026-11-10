import { useFetch } from "../../api";
import { Empty, Loading, PageHead, Pill, Stat } from "../../components/ui";

export default function Results() {
  const st = useFetch("/student/results/");
  if (st.loading || st.error) return <Loading state={st} />;
  const { results, gpa, credits } = st.data;
  return (
    <>
      <PageHead title="My results" sub="Results appear here once they are complete. A missing mark is never shown as a final grade." />
      <div className="grid">
        <Stat label="GPA" value={gpa ?? "n/a"} />
        <Stat label="Credits passed" value={credits} />
      </div>
      {results.length === 0 ? (
        <Empty>No results captured yet.</Empty>
      ) : (
        <div className="tw">
          <table>
            <thead>
              <tr><th>Year</th><th>Unit</th><th>CAT</th><th>Exam</th><th>Total</th><th>Grade</th><th>Status</th></tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td>{r.academic_year}</td>
                  <td>{r.unit.code} · {r.unit.title}</td>
                  <td>{r.cat ?? "–"}</td>
                  <td>{r.exam ?? "–"}</td>
                  <td>{r.total ?? "–"}</td>
                  <td>{r.grade ?? "–"}</td>
                  <td>
                    <Pill status={r.status} />
                    {r.status !== "complete" && <div className="note">{r.note}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
