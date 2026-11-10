import { Navigate, Route, Routes } from "react-router-dom";
import { HOME, useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";

import StudentDashboard from "./pages/student/Dashboard";
import Register from "./pages/student/Register";
import Results from "./pages/student/Results";
import Fees from "./pages/student/Fees";
import Graduation from "./pages/student/Graduation";
import Advisor from "./pages/student/Advisor";
import Requests from "./pages/student/Requests";
import Profile from "./pages/student/Profile";

import Units from "./pages/shared/Units";
import MarksSheet from "./pages/shared/MarksSheet";
import Cases from "./pages/shared/Cases";
import Audit from "./pages/shared/Audit";

import HodDashboard from "./pages/hod/Dashboard";
import Curriculum from "./pages/hod/Curriculum";

import Validation from "./pages/staff/Validation";
import Students from "./pages/staff/Students";
import Transcript from "./pages/staff/Transcript";
import StaffGraduation from "./pages/staff/Graduation";
import Users from "./pages/staff/Users";

function Root() {
  const { user, loading } = useAuth();
  if (loading) return <div className="spin">Loading…</div>;
  return <Navigate to={user ? HOME[user.role] : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Root />} />
      <Route path="/login" element={<Login />} />

      <Route path="/student" element={<Layout role="student" />}>
        <Route index element={<StudentDashboard />} />
        <Route path="register" element={<Register />} />
        <Route path="results" element={<Results />} />
        <Route path="fees" element={<Fees />} />
        <Route path="graduation" element={<Graduation />} />
        <Route path="advisor" element={<Advisor />} />
        <Route path="requests" element={<Requests />} />
        <Route path="profile" element={<Profile />} />
      </Route>

      <Route path="/lecturer" element={<Layout role="lecturer" />}>
        <Route index element={<Units base="/lecturer" />} />
        <Route path="marks/:unitId" element={<MarksSheet base="/lecturer" />} />
      </Route>

      <Route path="/hod" element={<Layout role="hod" />}>
        <Route index element={<HodDashboard />} />
        <Route path="cases" element={<Cases />} />
        <Route path="curriculum" element={<Curriculum />} />
        <Route path="audit" element={<Audit />} />
      </Route>

      <Route path="/staff" element={<Layout role="staff" />}>
        <Route index element={<Validation />} />
        <Route path="marks" element={<Units base="/staff" />} />
        <Route path="marks/:unitId" element={<MarksSheet base="/staff" />} />
        <Route path="students" element={<Students />} />
        <Route path="students/:id/transcript" element={<Transcript />} />
        <Route path="graduation" element={<StaffGraduation />} />
        <Route path="cases" element={<Cases />} />
        <Route path="users" element={<Users />} />
        <Route path="audit" element={<Audit />} />
      </Route>

      <Route path="*" element={<Root />} />
    </Routes>
  );
}
