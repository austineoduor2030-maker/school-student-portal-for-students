"""Pure-rule tests. Run with no Django installed:

    cd backend && python -m unittest portal.tests.test_rules -v
"""
import importlib.util
import pathlib
import unittest

# Load rules.py directly so this file works even without Django on the path.
_p = pathlib.Path(__file__).resolve().parent.parent / "rules.py"
_spec = importlib.util.spec_from_file_location("rules", _p)
rules = importlib.util.module_from_spec(_spec)
import sys

sys.modules["rules"] = rules  # dataclasses need the module registered
_spec.loader.exec_module(rules)


class MarkGate(unittest.TestCase):
    def test_complete(self):
        self.assertEqual(rules.mark_status(20, 50)[0], "complete")

    def test_missing_no_reason_is_blocked(self):
        self.assertEqual(rules.mark_status(20, None)[0], "blocked")

    def test_missing_with_approved_reason_is_pending(self):
        self.assertEqual(rules.mark_status(None, None, exception_approved=True)[0], "pending")

    def test_on_sheet_not_captured_is_blocked_even_with_reason(self):
        status, msg = rules.mark_status(20, None, on_score_sheet=True, exception_approved=True)
        self.assertEqual(status, "blocked")
        self.assertIn("score sheet", msg)

    def test_zero_is_a_real_mark(self):
        self.assertEqual(rules.mark_status(0, 0)[0], "complete")

    def test_value_ranges(self):
        self.assertTrue(rules.validate_mark_values(31, 10))
        self.assertTrue(rules.validate_mark_values(10, 71))
        self.assertTrue(rules.validate_mark_values(-1, 10))
        self.assertFalse(rules.validate_mark_values(30, 70))


class Grades(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(rules.total_and_grade(30, 40)[1], "A")
        self.assertEqual(rules.total_and_grade(29, 40)[1], "B")
        self.assertEqual(rules.total_and_grade(20, 20)[1], "D")
        self.assertEqual(rules.total_and_grade(19, 20)[1], "E")
        self.assertEqual(rules.total_and_grade(None, 20), (None, None, None))

    def test_gpa(self):
        self.assertEqual(rules.gpa([(4.0, 3), (2.0, 3)]), 3.0)
        self.assertIsNone(rules.gpa([]))


class Registration(unittest.TestCase):
    def base(self, **kw):
        args = dict(
            unit_code="CCS 210", prereq_codes=["CCS 110"], passed_codes={"CCS 110"},
            fees_balance=0, already_registered=False, credits_so_far=12, unit_credits=3,
        )
        args.update(kw)
        return rules.check_registration(**args)

    def test_ok(self):
        self.assertEqual(self.base(), [])

    def test_missing_prereq(self):
        self.assertEqual([i.code for i in self.base(passed_codes=set())], ["PREREQ_MISSING"])

    def test_waived_prereq(self):
        self.assertEqual(self.base(passed_codes=set(), waived_prereqs={"CCS 110"}), [])

    def test_fees(self):
        self.assertEqual([i.code for i in self.base(fees_balance=500)], ["FEES_OUTSTANDING"])

    def test_credit_limit(self):
        self.assertEqual([i.code for i in self.base(credits_so_far=22)], ["CREDIT_LIMIT"])

    def test_duplicate_and_passed(self):
        codes = [i.code for i in self.base(already_registered=True, passed_codes={"CCS 110", "CCS 210"})]
        self.assertIn("ALREADY_REGISTERED", codes)
        self.assertIn("ALREADY_PASSED", codes)


class Graduation(unittest.TestCase):
    def test_eligible(self):
        r = rules.graduation_audit(120, 120, [], [], [], 0)
        self.assertTrue(r["eligible"])
        self.assertEqual(r["progress_percent"], 100)

    def test_pending_does_not_block(self):
        r = rules.graduation_audit(120, 120, [], ["CCS 400"], [], 0)
        self.assertTrue(r["eligible"])
        self.assertFalse(r["issues"][0]["blocking"])

    def test_blocked_marks_and_fees_block(self):
        r = rules.graduation_audit(120, 117, ["CCS 499"], [], ["CCS 400"], 1000)
        self.assertFalse(r["eligible"])
        self.assertEqual(
            {i["code"] for i in r["issues"]},
            {"CREDITS_SHORT", "CORE_OUTSTANDING", "MARKS_BLOCKED", "FEES_OUTSTANDING"},
        )


class Transcript(unittest.TestCase):
    def test_ready_with_pending(self):
        r = rules.transcript_readiness({"A": "complete", "B": "pending"})
        self.assertTrue(r["ready"])
        self.assertEqual(r["pending_units"], ["B"])

    def test_not_ready_with_blocked(self):
        r = rules.transcript_readiness({"A": "complete", "B": "blocked"})
        self.assertFalse(r["ready"])
        self.assertEqual(r["blocked_units"], ["B"])


if __name__ == "__main__":
    unittest.main()
