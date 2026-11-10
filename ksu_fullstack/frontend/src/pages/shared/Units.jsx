import { Link } from "react-router-dom";
import { useFetch } from "../../api";
import { Empty, Loading, PageHead } from "../../components/ui";

/** Lists units whose marks the signed-in person may enter: a lecturer's own units, or all units for staff. */
export default function Units({ base }) {
  const st = useFetch("/marks/units/");
  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead
        title={base === "/lecturer" ? "My units" : "Enter / edit marks"}
        sub="Open a unit to enter CAT and exam marks. Blocked rows must be fixed before results can be released."
      />
      {st.data.length === 0 && <Empty>No units assigned to you yet.</Empty>}
      {st.data.map((u) => (
        <Link key={u.id} to={`${base}/marks/${u.id}`} className="card" style={{ display: "block" }}>
          <div className="row">
            <div>
              <b>{u.code} · {u.title}</b>
              <div className="note">{u.program} · {u.students} registered</div>
            </div>
            <div className="row-actions">
              {u.blocked > 0 && <span className="pill r">{u.blocked} blocked</span>}
              {u.pending > 0 && <span className="pill a">{u.pending} pending</span>}
              {u.blocked === 0 && u.pending === 0 && u.students > 0 && <span className="pill g">All complete</span>}
              {u.students === 0 && <span className="pill n">No students</span>}
            </div>
          </div>
        </Link>
      ))}
    </>
  );
}
