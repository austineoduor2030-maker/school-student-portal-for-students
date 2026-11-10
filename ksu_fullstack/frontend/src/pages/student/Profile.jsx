import { useEffect, useState } from "react";
import { api, useFetch } from "../../api";
import { Banner, Loading, PageHead } from "../../components/ui";

export default function Profile() {
  const st = useFetch("/student/profile/");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => { if (st.data) setPhone(st.data.next_of_kin_phone); }, [st.data]);

  async function save(e) {
    e.preventDefault();
    setError("");
    setOk("");
    try {
      await api("/student/profile/", { method: "PATCH", body: { next_of_kin_phone: phone } });
      setOk("Saved. You can now submit registrations.");
      st.reload();
    } catch (x) {
      setError(x.message);
    }
  }

  if (st.loading || st.error) return <Loading state={st} />;
  const p = st.data;
  const bad = phone.replace(/\D/g, "").length < 9;
  return (
    <>
      <PageHead title="Profile" sub="Details must be complete before you can register." />
      <div className="card">
        <div className="row"><span className="mu">Name</span><b>{p.name}</b></div>
        <div className="row"><span className="mu">Registration number</span><b>{p.reg_no}</b></div>
        <div className="row"><span className="mu">Programme</span><b>{p.program}</b></div>
        <div className="row"><span className="mu">Year / semester</span><b>{p.year} / {p.semester}</b></div>
      </div>
      <form className="card" onSubmit={save}>
        <h2>Next of kin</h2>
        <Banner>{error}</Banner>
        <Banner kind="g">{ok}</Banner>
        <label htmlFor="kin">Next of kin phone</label>
        <input id="kin" className={bad && phone ? "bad" : ""} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="07XX XXX XXX" inputMode="tel" />
        {bad && phone && <div className="note err-text">Enter a valid phone number to continue.</div>}
        <div style={{ marginTop: 12 }}><button className="btn" disabled={bad}>Save</button></div>
      </form>
    </>
  );
}
