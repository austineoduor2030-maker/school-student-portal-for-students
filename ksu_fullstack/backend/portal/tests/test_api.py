"""API tests. Run with:  python manage.py test portal"""
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from portal.models import AuditLog, CaseRequest, Mark
from portal.seed import build_demo


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.d = build_demo("test-pass-123")

    def login(self, username, password="test-pass-123"):
        r = self.client.post("/api/auth/login/", {"username": username, "password": password}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + r.data["token"])
        return r.data


class AuthTests(Base):
    def test_wrong_password_rejected(self):
        r = self.client.post("/api/auth/login/", {"username": "brian", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_student_can_sign_in_with_reg_no(self):
        data = self.login("CIT/0001/2024")
        self.assertEqual(data["user"]["role"], "student")

    def test_anonymous_cannot_read_api(self):
        self.assertEqual(self.client.get("/api/student/dashboard/").status_code, 401)

    def test_roles_are_separated(self):
        self.login("brian")
        self.assertEqual(self.client.get("/api/staff/users/").status_code, 403)
        self.assertEqual(self.client.get("/api/marks/units/").status_code, 403)
        self.login("lec1")
        self.assertEqual(self.client.get("/api/student/dashboard/").status_code, 403)
        self.assertEqual(self.client.get("/api/cases/").status_code, 403)


class RegistrationTests(Base):
    def test_prerequisite_blocks_registration(self):
        self.login("brian")
        unit = self.d["units"]["CIT 305"]
        r = self.client.post("/api/student/registrations/", {"unit_id": unit.id}, format="json")
        self.assertEqual(r.status_code, 422)
        codes = {i["code"] for i in r.data["issues"]}
        self.assertIn("PREREQ_MISSING", codes)

    def test_missing_profile_blocks_registration(self):
        self.login("brian")
        unit = self.d["units"]["CIT 240"]
        r = self.client.post("/api/student/registrations/", {"unit_id": unit.id}, format="json")
        self.assertEqual(r.status_code, 422)
        self.assertIn("PROFILE_INCOMPLETE", {i["code"] for i in r.data["issues"]})

    def test_registers_after_profile_completed(self):
        self.login("brian")
        bad = self.client.patch("/api/student/profile/", {"next_of_kin_phone": "123"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.client.patch("/api/student/profile/", {"next_of_kin_phone": "0711223344"}, format="json")
        self.assertEqual(ok.status_code, 200)
        unit = self.d["units"]["CIT 240"]
        r = self.client.post("/api/student/registrations/", {"unit_id": unit.id}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_fees_block_registration(self):
        self.login("amina")
        unit = self.d["units"]["CIT 240"]
        r = self.client.post("/api/student/registrations/", {"unit_id": unit.id}, format="json")
        self.assertEqual(r.status_code, 422)
        self.assertIn("FEES_OUTSTANDING", {i["code"] for i in r.data["issues"]})

    def test_waiver_approval_unblocks_prerequisite(self):
        self.login("brian")
        self.client.patch("/api/student/profile/", {"next_of_kin_phone": "0711223344"}, format="json")
        unit = self.d["units"]["CIT 305"]
        req = self.client.post("/api/student/requests/", {"unit_id": unit.id, "reason": "I did CIT 201 elsewhere."}, format="json")
        self.assertEqual(req.status_code, 201, req.content)
        # The student cannot approve their own request.
        self.assertEqual(self.client.post(f"/api/cases/{req.data['id']}/decide/", {"decision": "approved"}, format="json").status_code, 403)
        self.login("hod1")
        done = self.client.post(f"/api/cases/{req.data['id']}/decide/", {"decision": "approved", "note": "Verified."}, format="json")
        self.assertEqual(done.status_code, 200)
        self.login("brian")
        r = self.client.post("/api/student/registrations/", {"unit_id": unit.id}, format="json")
        self.assertEqual(r.status_code, 201, r.content)


class MarksGateTests(Base):
    def test_lecturer_only_sees_own_units(self):
        self.login("lec1")
        codes = {u["code"] for u in self.client.get("/api/marks/units/").data}
        self.assertIn("CIT 220", codes)
        self.assertNotIn("CIT 260", codes)
        other = self.d["units"]["CIT 260"]
        self.assertEqual(self.client.get(f"/api/marks/units/{other.id}/roster/").status_code, 404)

    def test_out_of_range_marks_rejected(self):
        self.login("lec1")
        u, s = self.d["units"]["CIT 220"], self.d["amina"]
        r = self.client.put("/api/marks/", {"unit_id": u.id, "student_id": s.id, "cat": 45, "exam": 50}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_missing_mark_blocks_then_complete_clears(self):
        self.login("lec1")
        u, s = self.d["units"]["CIT 220"], self.d["amina"]
        r = self.client.put("/api/marks/", {"unit_id": u.id, "student_id": s.id, "cat": 20, "exam": ""}, format="json")
        self.assertEqual(r.data["status"], "blocked")
        r = self.client.put("/api/marks/", {"unit_id": u.id, "student_id": s.id, "cat": 20, "exam": 50}, format="json")
        self.assertEqual(r.data["status"], "complete")

    def test_reason_becomes_pending_only_after_approval(self):
        self.login("lec1")
        u, s = self.d["units"]["CIT 220"], self.d["amina"]
        self.client.put("/api/marks/", {"unit_id": u.id, "student_id": s.id, "cat": 20, "exam": ""}, format="json")
        req = self.client.post("/api/marks/exceptions/", {"unit_id": u.id, "student_id": s.id, "reason": "Deferred: bereavement."}, format="json")
        self.assertEqual(req.status_code, 201, req.content)
        mark = Mark.objects.get(student=s, unit=u)
        self.assertEqual(mark.status, "blocked")  # asking is not enough
        self.login("lec1")
        self.assertEqual(self.client.post(f"/api/cases/{req.data['id']}/decide/", {"decision": "approved"}, format="json").status_code, 403)
        self.login("staff1")
        self.assertEqual(self.client.post(f"/api/cases/{req.data['id']}/decide/", {"decision": "approved", "note": "ok"}, format="json").status_code, 200)
        mark.refresh_from_db()
        self.assertEqual(mark.status, "pending")

    def test_reason_refused_when_value_is_on_score_sheet(self):
        self.login("lec2")
        u, s = self.d["units"]["CIT 260"], self.d["peter"]
        r = self.client.post("/api/marks/exceptions/", {"unit_id": u.id, "student_id": s.id, "reason": "Student was sick."}, format="json")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.data["code"], "ON_SCORE_SHEET")
        self.assertFalse(CaseRequest.objects.filter(student=s, unit=u).exists())

    def test_cannot_enter_marks_for_unregistered_student(self):
        self.login("lec1")
        u, s = self.d["units"]["CIT 240"], self.d["brian"]
        r = self.client.put("/api/marks/", {"unit_id": u.id, "student_id": s.id, "cat": 10, "exam": 10}, format="json")
        self.assertEqual(r.status_code, 400)


class StaffTests(Base):
    def test_transcript_release_blocked_until_marks_captured(self):
        self.login("staff1")
        peter = self.d["peter"]
        r = self.client.post(f"/api/staff/students/{peter.id}/transcript/release/")
        self.assertEqual(r.status_code, 422)
        self.assertIn("CIT 260", r.data["readiness"]["blocked_units"])
        self.assertTrue(AuditLog.objects.filter(action="transcript_blocked").exists())
        # Capture the missing exam from the score sheet; the pending CIT 240 does not block release.
        u = self.d["units"]["CIT 260"]
        self.client.put("/api/marks/", {"unit_id": u.id, "student_id": peter.id, "cat": 18, "exam": 40}, format="json")
        r = self.client.post(f"/api/staff/students/{peter.id}/transcript/release/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("CIT 240", r.data["readiness"]["pending_units"])

    def test_staff_cannot_change_own_role(self):
        self.login("staff1")
        r = self.client.patch(f"/api/staff/users/{self.d['staff'].id}/", {"role": "student"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_audit_log_is_read_only(self):
        self.login("staff1")
        entry = AuditLog.objects.first()
        with self.assertRaises(PermissionError):
            entry.delete()


class AdvisorTests(Base):
    def test_cites_rule_and_offers_waiver(self):
        self.login("brian")
        r = self.client.post("/api/student/ask/", {"question": "Can I register for CIT 305?"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("PREREQ_MISSING", r.data["citations"])
        self.assertEqual(r.data["suggested_action"]["type"], "request_waiver")

    def test_unknown_question_escalates_to_a_human(self):
        self.login("brian")
        r = self.client.post("/api/student/ask/", {"question": "Can I change my course to medicine?"}, format="json")
        self.assertTrue(r.data["escalate"])

    def test_students_see_only_their_own_fees(self):
        self.login("amina")
        self.assertEqual(self.client.get("/api/student/fees/").data["balance"], 15000.0)
        self.login("brian")
        self.assertEqual(self.client.get("/api/student/fees/").data["balance"], 0.0)
