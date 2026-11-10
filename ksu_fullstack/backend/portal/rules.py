"""Business rules as pure functions (no Django imports).

Keeping the rules here means they can be unit-tested without a database and
read by a non-programmer (HOD, registrar) to confirm the system matches policy.
Every result carries a `rule` code so the UI and the adviser can cite it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

PASS_MARK = 40
CAT_MAX = 30
EXAM_MAX = 70
MAX_CREDITS_PER_SEMESTER = 24

# Mark statuses
COMPLETE = "complete"   # CAT and exam both captured
PENDING = "pending"     # missing, but a human approved the reason
BLOCKED = "blocked"     # missing with no approved reason, or not captured


@dataclass
class Issue:
    code: str
    message: str
    blocking: bool = True

    def as_dict(self):
        return {"code": self.code, "message": self.message, "blocking": self.blocking}


# --------------------------------------------------------------------------
# Marks gate
# --------------------------------------------------------------------------
def mark_status(
    cat: Optional[float],
    exam: Optional[float],
    on_score_sheet: bool = False,
    exception_approved: bool = False,
) -> tuple[str, str]:
    """Return (status, explanation) for one student's mark in one unit.

    * both present                         -> complete
    * missing + on the score sheet         -> blocked (it exists, so capture it;
                                              a reason cannot excuse data that is available)
    * missing + no sheet entry + approved  -> pending (allowed to proceed)
    * missing + no sheet entry + no reason -> blocked
    """
    missing = [n for n, v in (("CAT", cat), ("Exam", exam)) if v is None]
    if not missing:
        return COMPLETE, "CAT and exam captured."
    what = " and ".join(missing)
    if on_score_sheet:
        return BLOCKED, (
            f"{what} is on the score sheet but has not been captured. "
            "Capture it from the sheet; a reason is not accepted when the data exists."
        )
    if exception_approved:
        return PENDING, f"{what} missing; reason approved by the HOD/staff. Allowed to proceed as pending."
    return BLOCKED, f"{what} missing and no approved reason. Request an exception or capture the mark."


def validate_mark_values(cat: Optional[float], exam: Optional[float]) -> list[str]:
    errors = []
    if cat is not None and not (0 <= cat <= CAT_MAX):
        errors.append(f"CAT must be between 0 and {CAT_MAX}.")
    if exam is not None and not (0 <= exam <= EXAM_MAX):
        errors.append(f"Exam must be between 0 and {EXAM_MAX}.")
    return errors


def total_and_grade(cat: Optional[float], exam: Optional[float]):
    """Return (total, letter, points) or (None, None, None) if a part is missing."""
    if cat is None or exam is None:
        return None, None, None
    total = cat + exam
    for floor, letter, pts in ((70, "A", 4.0), (60, "B", 3.0), (50, "C", 2.0), (PASS_MARK, "D", 1.0)):
        if total >= floor:
            return total, letter, pts
    return total, "E", 0.0


def gpa(results: Iterable[tuple[float, float]]) -> Optional[float]:
    """results = (grade_points, credits). Returns None when there are no credits."""
    pts = cr = 0.0
    for p, c in results:
        pts += p * c
        cr += c
    return round(pts / cr, 2) if cr else None


# --------------------------------------------------------------------------
# Registration gate
# --------------------------------------------------------------------------
def check_registration(
    unit_code: str,
    prereq_codes: Iterable[str],
    passed_codes: set[str],
    fees_balance: float,
    already_registered: bool,
    credits_so_far: int,
    unit_credits: int,
    waived_prereqs: Optional[set[str]] = None,
) -> list[Issue]:
    waived = waived_prereqs or set()
    issues: list[Issue] = []
    if already_registered:
        issues.append(Issue("ALREADY_REGISTERED", f"{unit_code} is already registered for this semester."))
    if unit_code in passed_codes:
        issues.append(Issue("ALREADY_PASSED", f"You have already passed {unit_code}."))
    for p in prereq_codes:
        if p not in passed_codes and p not in waived:
            issues.append(Issue("PREREQ_MISSING", f"{unit_code} requires {p}, which you have not passed."))
    if fees_balance > 0:
        issues.append(Issue("FEES_OUTSTANDING", f"Fee balance of KES {fees_balance:,.0f} must be cleared first."))
    if credits_so_far + unit_credits > MAX_CREDITS_PER_SEMESTER:
        issues.append(
            Issue(
                "CREDIT_LIMIT",
                f"Adding {unit_code} would take you to {credits_so_far + unit_credits} credits; "
                f"the limit is {MAX_CREDITS_PER_SEMESTER}.",
            )
        )
    return issues


def check_profile(next_of_kin_phone: Optional[str]) -> list[Issue]:
    """Data that must exist before a student may submit a registration."""
    digits = "".join(ch for ch in (next_of_kin_phone or "") if ch.isdigit())
    if len(digits) < 9:
        return [Issue("PROFILE_INCOMPLETE", "Add a valid next of kin phone number in your profile before registering.")]
    return []


# --------------------------------------------------------------------------
# Graduation audit
# --------------------------------------------------------------------------
def graduation_audit(
    required_credits: int,
    passed_credits: int,
    outstanding_core_units: list[str],
    pending_mark_units: list[str],
    blocked_mark_units: list[str],
    fees_balance: float,
) -> dict:
    issues: list[Issue] = []
    if passed_credits < required_credits:
        issues.append(
            Issue("CREDITS_SHORT", f"{required_credits - passed_credits} credits short of the {required_credits} required.")
        )
    if outstanding_core_units:
        issues.append(Issue("CORE_OUTSTANDING", "Core units not yet passed: " + ", ".join(outstanding_core_units) + "."))
    if blocked_mark_units:
        issues.append(Issue("MARKS_BLOCKED", "Marks not captured for: " + ", ".join(blocked_mark_units) + "."))
    if pending_mark_units:
        issues.append(
            Issue("MARKS_PENDING", "Marks pending (approved reason) for: " + ", ".join(pending_mark_units) + ".", blocking=False)
        )
    if fees_balance > 0:
        issues.append(Issue("FEES_OUTSTANDING", f"Fee balance of KES {fees_balance:,.0f} outstanding."))
    blocking = [i for i in issues if i.blocking]
    return {
        "eligible": not blocking,
        "progress_percent": min(100, round(100 * passed_credits / required_credits)) if required_credits else 0,
        "issues": [i.as_dict() for i in issues],
    }


def transcript_readiness(mark_statuses: dict[str, str]) -> dict:
    """mark_statuses maps unit code -> complete|pending|blocked.

    A transcript can be released only when nothing is blocked. Pending units are
    printed with a 'results pending' line, as per the approved exception."""
    blocked = sorted(c for c, s in mark_statuses.items() if s == BLOCKED)
    pending = sorted(c for c, s in mark_statuses.items() if s == PENDING)
    return {"ready": not blocked, "blocked_units": blocked, "pending_units": pending}
