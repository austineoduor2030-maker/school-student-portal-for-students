"""Reads the database and feeds plain values to rules.py. No HTTP in here."""
from django.conf import settings

from . import rules
from .models import CaseRequest, Mark, Registration, Student, Unit


def current_year():
    return getattr(settings, "CURRENT_ACADEMIC_YEAR", "2026/2027")


def full_name(user):
    return user.get_full_name() or user.username


def user_payload(u):
    data = {
        "id": u.id,
        "username": u.username,
        "name": full_name(u),
        "role": u.role,
        "department": u.department,
        "university": u.university.name if u.university else None,
    }
    student = getattr(u, "student", None) if u.role == "student" else None
    if student:
        data.update(
            reg_no=student.reg_no,
            program=student.program.name,
            year=student.year,
            semester=student.semester,
        )
    return data


def student_state(student):
    """Everything derived from a student's captured marks."""
    passed, failed, points, statuses = set(), [], [], {}
    credits = 0
    for m in student.marks.select_related("unit"):
        statuses[m.unit.code] = m.status
        if m.status == rules.COMPLETE:
            _, letter, pts = rules.total_and_grade(float(m.cat), float(m.exam))
            points.append((pts, m.unit.credits))
            if letter == "E":
                failed.append(m.unit.code)
            else:
                passed.add(m.unit.code)
                credits += m.unit.credits
    return {
        "passed": passed,
        "failed": failed,
        "credits": credits,
        "gpa": rules.gpa(points),
        "statuses": statuses,
    }


def registration_issues(student, unit, state=None, include_profile=False):
    state = state or student_state(student)
    regs = list(student.registrations.filter(academic_year=current_year()).select_related("unit"))
    prereqs = list(unit.prerequisites.values_list("code", flat=True))
    waived = set()
    if student.requests.filter(kind=CaseRequest.Kind.PREREQ_WAIVER, unit=unit, status=CaseRequest.Status.APPROVED).exists():
        waived = set(prereqs)
    issues = rules.check_registration(
        unit.code,
        prereqs,
        state["passed"],
        float(student.fees_balance),
        any(r.unit_id == unit.id for r in regs),
        sum(r.unit.credits for r in regs),
        unit.credits,
        waived,
    )
    if include_profile:
        issues += rules.check_profile(student.next_of_kin_phone)
    return issues


def graduation_for(student, state=None):
    state = state or student_state(student)
    program = student.program
    core = list(program.units.filter(is_core=True).values_list("code", flat=True))
    pending = sorted(c for c, s in state["statuses"].items() if s == rules.PENDING)
    blocked = sorted(c for c, s in state["statuses"].items() if s == rules.BLOCKED)
    outstanding = [c for c in core if c not in state["passed"] and c not in pending and c not in blocked]
    result = rules.graduation_audit(
        program.required_credits, state["credits"], outstanding, pending, blocked, float(student.fees_balance)
    )
    result.update(
        passed_credits=state["credits"],
        required_credits=program.required_credits,
        gpa=state["gpa"],
    )
    return result


def _f(v):
    return None if v is None else float(v)


def mark_payload(student, unit, mark):
    """One row of a marks sheet. `mark` may be None (nothing captured yet)."""
    base = {
        "student": {"id": student.id, "reg_no": student.reg_no, "name": full_name(student.user)},
        "unit": {"id": unit.id, "code": unit.code, "title": unit.title},
    }
    if mark is None:
        return {
            **base,
            "id": None,
            "cat": None,
            "exam": None,
            "total": None,
            "grade": None,
            "on_score_sheet": False,
            "status": rules.BLOCKED,
            "note": "Nothing captured yet.",
            "request": None,
        }
    total, letter, _ = rules.total_and_grade(_f(mark.cat), _f(mark.exam))
    req = mark.requests.filter(kind=CaseRequest.Kind.MISSING_MARK).first()
    return {
        **base,
        "id": mark.id,
        "cat": _f(mark.cat),
        "exam": _f(mark.exam),
        "total": total,
        "grade": letter,
        "on_score_sheet": mark.on_score_sheet,
        "status": mark.status,
        "note": mark.status_note,
        "request": {"id": req.id, "status": req.status, "reason": req.reason} if req else None,
    }


def roster(unit):
    """Every student registered for `unit` this year, with their mark (or none)."""
    rows = []
    regs = unit.registration_set.filter(academic_year=current_year()).select_related("student__user")
    for reg in regs:
        mark = Mark.objects.filter(student=reg.student, unit=unit, academic_year=reg.academic_year).first()
        rows.append(mark_payload(reg.student, unit, mark))
    return rows


def units_visible_to(user):
    qs = Unit.objects.filter(university=user.university)
    if user.role == "lecturer":
        qs = qs.filter(lecturer=user)
    return qs


def students_in_scope(user):
    """Staff see the whole university; an HOD sees their department's programmes."""
    qs = Student.objects.filter(program__university=user.university).select_related("user", "program")
    if user.role == "hod" and user.department:
        qs = qs.filter(program__department=user.department)
    return qs
