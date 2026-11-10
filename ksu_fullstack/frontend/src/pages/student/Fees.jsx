import { useFetch } from "../../api";
import { Loading, PageHead, Stat, money } from "../../components/ui";

export default function Fees() {
  const st = useFetch("/student/fees/");
  if (st.loading || st.error) return <Loading state={st} />;
  const f = st.data;
  return (
    <>
      <PageHead title="Fees" sub="Your balance as recorded by the finance office." />
      <div className="grid">
        <Stat label="Outstanding balance" value={f.cleared ? "Cleared" : money(f.balance)} />
      </div>
      {f.cleared ? (
        <div className="box g">No holds on your account.</div>
      ) : (
        f.holds.map((h) => (
          <div key={h.code} className="box r">
            <b>{h.code}</b> · {h.message}
          </div>
        ))
      )}
      <p className="note">Paid but still showing a balance? Visit the finance office with your receipt; staff update the balance here.</p>
    </>
  );
}
