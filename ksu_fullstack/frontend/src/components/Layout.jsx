import { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { HOME, useAuth } from "../auth";

const NAV = {
  student: [
    ["/student", "Dashboard", true],
    ["/student/register", "Register units"],
    ["/student/results", "My results"],
    ["/student/fees", "Fees"],
    ["/student/graduation", "Graduation check"],
    ["/student/advisor", "Ask advisor"],
    ["/student/requests", "My requests"],
    ["/student/profile", "Profile"],
  ],
  lecturer: [
    ["/lecturer", "My units", true],
  ],
  hod: [
    ["/hod", "Overview", true],
    ["/hod/cases", "Approvals"],
    ["/hod/curriculum", "Curriculum"],
    ["/hod/audit", "Audit log"],
  ],
  staff: [
    ["/staff", "Validation queue", true],
    ["/staff/marks", "Enter / edit marks"],
    ["/staff/students", "Students & transcripts"],
    ["/staff/graduation", "Graduation clearance"],
    ["/staff/cases", "Exceptions"],
    ["/staff/users", "Users & roles"],
    ["/staff/audit", "Audit log"],
  ],
};

const ROLE_LABEL = { student: "Student portal", lecturer: "Lecturer portal", hod: "HOD portal", staff: "ICT / Registry" };

function useTheme() {
  const read = () => {
    try { return localStorage.getItem("ksu_theme") === "dark"; } catch { return false; }
  };
  const [dark, setDark] = useState(read);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("ksu_theme", dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);
  return [dark, setDark];
}

export function ThemeButton() {
  const [dark, setDark] = useTheme();
  return <button className="tbtn" onClick={() => setDark(!dark)}>{dark ? "Light mode" : "Dark mode"}</button>;
}

/** Route guard + shell. `role` is the only role allowed in this section. */
export default function Layout({ role }) {
  const { user, loading, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);

  if (loading) return <div className="spin">Loading…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (user.role !== role) return <Navigate to={HOME[user.role]} replace />;

  const initials = user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const details = user.role === "student"
    ? [user.reg_no, user.program, `Year ${user.year}, Semester ${user.semester}`].filter(Boolean).join(" · ")
    : [ROLE_LABEL[role], user.department].filter(Boolean).join(" · ");
  return (
    <div className="shell">
      <aside className={`side${open ? " open" : ""}`}>
        <div className="side-title">
          <div className="logo">KSU</div>
          <div>Kisii University<small>{ROLE_LABEL[role]}</small></div>
        </div>
        <nav>
          {NAV[role].map(([to, label, end]) => (
            <NavLink key={to} to={to} end={!!end} className={({ isActive }) => (isActive ? "on" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">
          <ThemeButton />
          <button className="tbtn" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <div className="content">
        <div className="mbar">
          <button className="tbtn" onClick={() => setOpen(!open)} aria-label="Menu">Menu</button>
          Kisii University
        </div>
        <header className="welcome">
          <div>
            <h1>Welcome, {user.name.split(" ")[0]}</h1>
            <p>{details}</p>
          </div>
          <div className="avatar">{initials}</div>
        </header>
        <hr className="rule" />
        <main className="main"><Outlet /></main>
      </div>
    </div>
  );
}
