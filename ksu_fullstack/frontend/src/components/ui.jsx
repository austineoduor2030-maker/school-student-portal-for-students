import { Link } from "react-router-dom";

export const STATUS = {
  complete: { cls: "g", label: "Complete" },
  pending: { cls: "a", label: "Pending (reason approved)" },
  blocked: { cls: "r", label: "Blocked" },
  requested: { cls: "a", label: "Awaiting decision" },
  approved: { cls: "g", label: "Approved" },
  rejected: { cls: "r", label: "Rejected" },
};

export function Pill({ status, children, cls }) {
  const s = STATUS[status];
  return <span className={`pill ${cls || (s && s.cls) || "n"}`}>{children || (s && s.label) || status}</span>;
}

export function PageHead({ title, sub }) {
  return (
    <>
      <h1>{title}</h1>
      {sub && <p className="sub">{sub}</p>}
    </>
  );
}

export function Loading({ state }) {
  if (state.loading) return <div className="spin">Loading…</div>;
  if (state.error) {
    return (
      <div className="banner r">
        {state.error.message} <button className="sm" onClick={state.reload}>Try again</button>
      </div>
    );
  }
  return null;
}

export function Banner({ kind = "r", children }) {
  if (!children) return null;
  return <div className={`banner ${kind}`}>{children}</div>;
}

export function Issues({ issues }) {
  if (!issues || !issues.length) return null;
  return (
    <div style={{ marginTop: 8 }}>
      {issues.map((i, n) => (
        <div key={n} style={{ marginBottom: 4 }}>
          <span className={`pill ${i.blocking === false ? "a" : "r"}`}>{i.code}</span> <span className="note" style={{ fontSize: 12 }}>{i.message}</span>
        </div>
      ))}
    </div>
  );
}

export function Stat({ label, value, bar }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <b>{value}</b>
      {bar !== undefined && <div className="bar"><i style={{ width: `${Math.min(100, bar)}%` }} /></div>}
    </div>
  );
}

export function Attention({ item }) {
  const cls = { red: "r", amber: "a", green: "g" }[item.level] || "a";
  return (
    <Link to={item.link} className={`box ${cls}`} style={{ display: "block" }}>
      <div className="row">
        <span>{item.text}</span>
        <span className={`pill ${cls}`}>{item.code}</span>
      </div>
    </Link>
  );
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function money(n) {
  return `KES ${Number(n || 0).toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
}

export function when(iso) {
  return iso ? new Date(iso).toLocaleString("en-KE", { dateStyle: "medium", timeStyle: "short" }) : "";
}
