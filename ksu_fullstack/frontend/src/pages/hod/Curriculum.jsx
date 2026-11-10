import { useFetch } from "../../api";
import { Loading, PageHead } from "../../components/ui";

export default function Curriculum() {
  const st = useFetch("/hod/curriculum/");
  if (st.loading || st.error) return <Loading state={st} />;
  return (
    <>
      <PageHead title="Curriculum" sub="Units, prerequisites and who teaches them. Edit through the admin site." />
      <div className="tw">
        <table>
          <thead><tr><th>Unit</th><th>Year / Sem</th><th>Credits</th><th>Type</th><th>Prerequisites</th><th>Lecturer</th></tr></thead>
          <tbody>
            {st.data.map((u) => (
              <tr key={u.id}>
                <td><b>{u.code}</b><div className="note">{u.title}</div></td>
                <td>{u.year} / {u.semester}</td>
                <td>{u.credits}</td>
                <td>{u.is_core ? "Core" : "Elective"}</td>
                <td>{u.prerequisites.join(", ") || "None"}</td>
                <td>{u.lecturer || <span className="pill a">Unassigned</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
