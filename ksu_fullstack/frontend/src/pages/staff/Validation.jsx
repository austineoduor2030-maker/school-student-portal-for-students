import { Link } from "react-router-dom";
import { useFetch } from "../../api";
import { Empty, Loading, PageHead, Pill } from "../../components/ui";

/** Everything that is incomplete, grouped by unit, so ICT knows exactly what to fix and where. */
export default function Validation() {
  const st = useFetch("/staff/validation/");
  if (st.loading || st.error) return <Loading state={st} />;
  const total = st.data.reduce((n, g) => n + g.rows.filter((r) => r.status === "blocked").length, 0);
  return (
    <>
      <PageHead title="Validation queue" sub="Nothing moves to transcripts or graduation while a row here is blocked." />
      {st.data.length === 0 ? (
        <div className="box g">All marks are complete. Nothing is blocking.</div>
      ) : (
        <div className={`box ${total ? "r" : "a"}`}>{total} blocked mark(s) across {st.data.length} unit(s).</div>
      )}
      {st.data.map((g) => (
        <div className="card" key={g.unit.id}>
          <div className="row">
            <div>
              <b>{g.unit.code} · {g.unit.title}</b>
              <div className="note">Lecturer: {g.lecturer || "unassigned"}</div>
            </div>
            <Link className="sm" to={`/staff/marks/${g.unit.id}`}>Open marks sheet</Link>
          </div>
          {g.rows.map((r) => (
            <div className="check" key={r.student.id}>
              <Pill status={r.status} />
              <div>
                <b>{r.student.name}</b> <span className="note">{r.student.reg_no}</span>
                <div className="note" style={{ fontSize: 12 }}>{r.note}</div>
              </div>
            </div>
          ))}
        </div>
      ))}
      {st.data.length === 0 && <Empty>You are all caught up.</Empty>}
    </>
  );
}
