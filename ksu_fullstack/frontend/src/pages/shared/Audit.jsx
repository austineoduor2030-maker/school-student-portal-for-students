import { useFetch } from "../../api";
import { Empty, Loading, PageHead, when } from "../../components/ui";

export default function Audit() {
  const st = useFetch("/audit/");
  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead title="Audit log" sub="Every gate decision and human decision. Entries cannot be edited or deleted." />
      {st.data.length === 0 ? <Empty>No activity yet.</Empty> : (
        <div className="tw">
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Detail</th></tr></thead>
            <tbody>
              {st.data.map((a) => (
                <tr key={a.id}>
                  <td>{when(a.created_at)}</td>
                  <td>{a.actor}</td>
                  <td><span className="pill n">{a.action}</span></td>
                  <td>{a.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
