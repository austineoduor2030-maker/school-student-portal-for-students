"""REST endpoints. Every write re-runs the rules server-side; the UI checks are only a convenience."""
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status as http
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import advisor, rules, services
from .models import AuditLog, CaseRequest, Mark, Registration, Student, Unit, User, audit
from .permissions import CanEnterMarks, IsDecider, IsHod, IsHodOrStaff, IsStaff, IsStudent


def bad(message, code=http.HTTP_400_BAD_REQUEST, **extra):
    return Response({"detail": message, **extra}, status=code)


def number(value, label):
    """'' / None -> None (missing). Otherwise a float, or ValueError with a readable message."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")


def my_student(request):
    return request.user.student


# ==========================================================================
# Auth
# ==========================================================================
@api_view(["POST"])
@authentication_classes([])  # a stale token in the browser must not block signing in
@permission_classes([AllowAny])
def login(request):
    ident = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not ident or not password:
        return bad("Enter your username (or registration number) and password.")
    # Students may sign in with their registration number.
    by_reg = Student.objects.filter(reg_no__iexact=ident).select_related("user").first()
    username = by_reg.user.username if by_reg else ident
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return bad("Wrong username or password.", http.HTTP_401_UNAUTHORIZED)
    Token.objects.filter(user=user).delete()  # one live session per user
    token = Token.objects.create(user=user)
    audit(user, "login", f"{user.username} signed in")
    return Response({"token": token.key, "user": services.user_payload(user)})


@api_view(["POST"])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=http.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response(services.user_payload(request.user))


# ==========================================================================
# Student
# ==========================================================================
@api_view(["GET"])
@permission_classes([IsStudent])
def student_dashboard(request):
    s = my_student(request)
    state = services.student_state(s)
    grad = services.graduation_for(s, state)
    year = services.current_year()
    regs = s.registrations.filter(academic_year=year).select_related("unit")

    attention = []
    for i in rules.check_profile(s.next_of_kin_phone):
        attention.append({"level": "amber", "code": i.code, "text": i.message, "link": "/student/profile"})
    if float(s.fees_balance) > 0:
        attention.append({
            "level": "red", "code": "FEES_OUTSTANDING",
            "text": f"Fee balance of KES {float(s.fees_balance):,.0f} blocks registration.", "link": "/student/fees",
        })
    held = [c for c, st in state["statuses"].items() if st != rules.COMPLETE]
    if held:
        attention.append({
            "level": "amber", "code": "MARKS_INCOMPLETE",
            "text": "Results not final for: " + ", ".join(sorted(held)) + ".", "link": "/student/results",
        })
    if state["failed"]:
        attention.append({
            "level": "red", "code": "FAILED_UNITS",
            "text": "Failed: " + ", ".join(sorted(state["failed"])) + ". Re-register before units that need them.",
            "link": "/student/register",
        })
    if not regs:
        attention.append({
            "level": "amber", "code": "NOT_REGISTERED",
            "text": "You have not registered any units this semester.", "link": "/student/register",
        })
    if grad["eligible"]:
        attention.append({"level": "green", "code": "GRAD_OK", "text": "You meet every graduation requirement on record.", "link": "/student/graduation"})

    return Response({
        "name": services.full_name(request.user),
        "reg_no": s.reg_no,
        "program": s.program.name,
        "year": s.year,
        "semester": s.semester,
        "academic_year": year,
        "credits": state["credits"],
        "required_credits": s.program.required_credits,
        "progress_percent": grad["progress_percent"],
        "gpa": state["gpa"],
        "fees_balance": float(s.fees_balance),
        "registered_credits": sum(r.unit.credits for r in regs),
        "attention": attention,
    })


@api_view(["GET"])
@permission_classes([IsStudent])
def student_units(request):
    """Units this student could register for, each with the rules' verdict."""
    s = my_student(request)
    state = services.student_state(s)
    year = services.current_year()
    registered = {r.unit_id: r.id for r in s.registrations.filter(academic_year=year)}
    candidates = s.program.units.filter(year=s.year, semester=s.semester) | s.program.units.filter(
        year__lt=s.year
    ).exclude(code__in=state["passed"])
    out = []
    for u in candidates.distinct().order_by("year", "semester", "code"):
        issues = services.registration_issues(s, u, state)
        waiver = s.requests.filter(kind=CaseRequest.Kind.PREREQ_WAIVER, unit=u).first()
        out.append({
            "id": u.id, "code": u.code, "title": u.title, "credits": u.credits,
            "year": u.year, "semester": u.semester, "is_core": u.is_core,
            "prerequisites": list(u.prerequisites.values_list("code", flat=True)),
            "registration_id": registered.get(u.id),
            "passed": u.code in state["passed"],
            "eligible": not any(i.blocking for i in issues),
            "issues": [i.as_dict() for i in issues],
            "waiver": {"id": waiver.id, "status": waiver.status} if waiver else None,
        })
    return Response({
        "units": out,
        "profile_issues": [i.as_dict() for i in rules.check_profile(s.next_of_kin_phone)],
        "max_credits": rules.MAX_CREDITS_PER_SEMESTER,
    })


@api_view(["POST"])
@permission_classes([IsStudent])
def student_register(request):
    s = my_student(request)
    unit = Unit.objects.filter(pk=request.data.get("unit_id"), program=s.program).first()
    if not unit:
        return bad("That unit is not in your programme.", http.HTTP_404_NOT_FOUND)
    issues = services.registration_issues(s, unit, include_profile=True)
    blocking = [i for i in issues if i.blocking]
    if blocking:
        audit(request.user, "registration_blocked", f"{s.reg_no} {unit.code}: " + ",".join(i.code for i in blocking))
        return Response(
            {"detail": "Registration blocked until these are fixed.", "issues": [i.as_dict() for i in blocking]},
            status=http.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    reg = Registration.objects.create(student=s, unit=unit, academic_year=services.current_year())
    audit(request.user, "registered", f"{s.reg_no} registered {unit.code}")
    return Response({"id": reg.id, "unit_id": unit.id}, status=http.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsStudent])
def student_unregister(request, pk):
    reg = Registration.objects.filter(pk=pk, student=my_student(request)).select_related("unit").first()
    if not reg:
        return bad("Registration not found.", http.HTTP_404_NOT_FOUND)
    if Mark.objects.filter(student=reg.student, unit=reg.unit, academic_year=reg.academic_year).exists():
        return bad("This unit already has marks and can no longer be dropped.", http.HTTP_409_CONFLICT)
    audit(request.user, "unregistered", f"{reg.student.reg_no} dropped {reg.unit.code}")
    reg.delete()
    return Response(status=http.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsStudent])
def student_results(request):
    s = my_student(request)
    rows = []
    for m in s.marks.select_related("unit").order_by("academic_year", "unit__code"):
        row = services.mark_payload(s, m.unit, m)
        row["academic_year"] = m.academic_year
        row["credits"] = m.unit.credits
        # Students see the status and reason, never other people's data.
        del row["student"]
        rows.append(row)
    state = services.student_state(s)
    return Response({"results": rows, "gpa": state["gpa"], "credits": state["credits"]})


@api_view(["GET"])
@permission_classes([IsStudent])
def student_graduation(request):
    return Response(services.graduation_for(my_student(request)))


@api_view(["GET"])
@permission_classes([IsStudent])
def student_fees(request):
    bal = float(my_student(request).fees_balance)
    return Response({
        "balance": bal,
        "cleared": bal <= 0,
        "holds": [] if bal <= 0 else [{"code": "FEES_OUTSTANDING", "message": "Registration and graduation are blocked until the balance is cleared."}],
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsStudent])
def student_profile(request):
    s = my_student(request)
    if request.method == "PATCH":
        phone = (request.data.get("next_of_kin_phone") or "").strip()
        issues = rules.check_profile(phone)
        if issues:
            return bad(issues[0].message, issues=[i.as_dict() for i in issues])
        s.next_of_kin_phone = phone
        s.save(update_fields=["next_of_kin_phone"])
        audit(request.user, "profile_updated", f"{s.reg_no} updated next of kin")
    return Response({
        **services.user_payload(request.user),
        "email": request.user.email,
        "next_of_kin_phone": s.next_of_kin_phone,
        "profile_issues": [i.as_dict() for i in rules.check_profile(s.next_of_kin_phone)],
    })


@api_view(["GET", "POST"])
@permission_classes([IsStudent])
def student_requests(request):
    s = my_student(request)
    if request.method == "POST":
        unit = Unit.objects.filter(pk=request.data.get("unit_id"), program=s.program).first()
        reason = (request.data.get("reason") or "").strip()
        if not unit:
            return bad("Choose a unit from your programme.")
        if len(reason) < 10:
            return bad("Explain your request in at least 10 characters.")
        issues = services.registration_issues(s, unit)
        if not any(i.code == "PREREQ_MISSING" for i in issues):
            return bad("This unit has no missing prerequisite, so no waiver is needed.")
        if s.requests.filter(kind=CaseRequest.Kind.PREREQ_WAIVER, unit=unit, status=CaseRequest.Status.REQUESTED).exists():
            return bad("You already have an open request for this unit.", http.HTTP_409_CONFLICT)
        req = CaseRequest.objects.create(
            university=request.user.university, kind=CaseRequest.Kind.PREREQ_WAIVER, student=s, unit=unit,
            reason=reason, requested_by=request.user,
        )
        audit(request.user, "waiver_requested", f"{s.reg_no} asked for a prerequisite waiver on {unit.code}")
        return Response(case_payload(req), status=http.HTTP_201_CREATED)
    return Response([case_payload(r) for r in s.requests.select_related("unit", "student__user", "decided_by")])


@api_view(["POST"])
@permission_classes([IsStudent])
def student_ask(request):
    question = (request.data.get("question") or "").strip()
    if not question:
        return bad("Type a question first.")
    if len(question) > 500:
        return bad("Keep your question under 500 characters.")
    result = advisor.answer(my_student(request), question)
    audit(request.user, "advisor_asked", f"{my_student(request).reg_no}: {question[:200]}" + (" [escalated]" if result["escalate"] else ""))
    return Response(result)


# ==========================================================================
# Cases (exceptions & waivers)
# ==========================================================================
def case_payload(c):
    return {
        "id": c.id,
        "kind": c.kind,
        "kind_label": c.get_kind_display(),
        "status": c.status,
        "reason": c.reason,
        "student": {"id": c.student_id, "reg_no": c.student.reg_no, "name": services.full_name(c.student.user)},
        "unit": {"id": c.unit_id, "code": c.unit.code, "title": c.unit.title},
        "mark_id": c.mark_id,
        "requested_by": services.full_name(c.requested_by),
        "decided_by": services.full_name(c.decided_by) if c.decided_by else None,
        "decision_note": c.decision_note,
        "created_at": c.created_at,
        "decided_at": c.decided_at,
    }


@api_view(["GET"])
@permission_classes([IsDecider])
def cases(request):
    qs = CaseRequest.objects.filter(university=request.user.university).select_related(
        "unit", "student__user", "requested_by", "decided_by"
    )
    wanted = request.query_params.get("status")
    if wanted:
        qs = qs.filter(status=wanted)
    if request.user.role == "hod" and request.user.department:
        qs = qs.filter(student__program__department=request.user.department)
    return Response([case_payload(c) for c in qs[:200]])


@api_view(["POST"])
@permission_classes([IsDecider])
def case_decide(request, pk):
    c = CaseRequest.objects.filter(pk=pk, university=request.user.university).select_related(
        "unit", "student__user", "requested_by", "decided_by", "mark"
    ).first()
    if not c:
        return bad("Request not found.", http.HTTP_404_NOT_FOUND)
    decision = request.data.get("decision")
    note = (request.data.get("note") or "").strip()
    if decision not in ("approved", "rejected"):
        return bad("Decision must be 'approved' or 'rejected'.")
    if c.status != CaseRequest.Status.REQUESTED:
        return bad("This request has already been decided.", http.HTTP_409_CONFLICT)
    if c.requested_by_id == request.user.id:
        return bad("You cannot decide a request you raised yourself.", http.HTTP_403_FORBIDDEN)
    if decision == "rejected" and not note:
        return bad("Give a short reason when rejecting, so the person knows what to fix.")
    c.status = decision
    c.decided_by = request.user
    c.decision_note = note[:300]
    c.decided_at = timezone.now()
    c.save()
    if c.mark_id:
        c.mark.save()  # recompute: an approved reason turns blocked into pending
    audit(request.user, f"case_{decision}", f"{c.get_kind_display()} #{c.id} for {c.student.reg_no} {c.unit.code}")
    return Response(case_payload(c))


@api_view(["GET"])
@permission_classes([IsHodOrStaff])
def audit_log(request):
    qs = AuditLog.objects.filter(university=request.user.university).select_related("actor")[:150]
    return Response([
        {"id": a.id, "actor": services.full_name(a.actor) if a.actor else "system", "action": a.action,
         "detail": a.detail, "created_at": a.created_at}
        for a in qs
    ])


# ==========================================================================
# Marks (lecturer + staff)
# ==========================================================================
@api_view(["GET"])
@permission_classes([CanEnterMarks])
def mark_units(request):
    out = []
    for u in services.units_visible_to(request.user).select_related("program"):
        rows = services.roster(u)
        out.append({
            "id": u.id, "code": u.code, "title": u.title, "program": u.program.name,
            "students": len(rows),
            "blocked": sum(1 for r in rows if r["status"] == rules.BLOCKED),
            "pending": sum(1 for r in rows if r["status"] == rules.PENDING),
        })
    return Response(out)


@api_view(["GET"])
@permission_classes([CanEnterMarks])
def unit_roster(request, pk):
    unit = services.units_visible_to(request.user).filter(pk=pk).first()
    if not unit:
        return bad("Unit not found, or you do not teach it.", http.HTTP_404_NOT_FOUND)
    rows = services.roster(unit)
    return Response({
        "unit": {"id": unit.id, "code": unit.code, "title": unit.title},
        "limits": {"cat_max": rules.CAT_MAX, "exam_max": rules.EXAM_MAX},
        "rows": rows,
        "can_submit": all(r["status"] != rules.BLOCKED for r in rows),
        "blocked": [r["student"]["reg_no"] for r in rows if r["status"] == rules.BLOCKED],
    })


@api_view(["PUT"])
@permission_classes([CanEnterMarks])
def save_mark(request):
    unit = services.units_visible_to(request.user).filter(pk=request.data.get("unit_id")).first()
    if not unit:
        return bad("Unit not found, or you do not teach it.", http.HTTP_404_NOT_FOUND)
    student = Student.objects.filter(pk=request.data.get("student_id"), program__university=request.user.university).first()
    if not student:
        return bad("Student not found.", http.HTTP_404_NOT_FOUND)
    year = services.current_year()
    if not Registration.objects.filter(student=student, unit=unit, academic_year=year).exists():
        return bad(f"{student.reg_no} is not registered for {unit.code} this year, so marks cannot be entered.")
    try:
        cat = number(request.data.get("cat"), "CAT")
        exam = number(request.data.get("exam"), "Exam")
    except ValueError as exc:
        return bad(str(exc))
    errors = rules.validate_mark_values(cat, exam)
    if errors:
        return bad(" ".join(errors), errors=errors)
    mark, _ = Mark.objects.get_or_create(student=student, unit=unit, academic_year=year)
    mark.cat, mark.exam = cat, exam
    if "on_score_sheet" in request.data:
        mark.on_score_sheet = bool(request.data.get("on_score_sheet"))
    mark.entered_by = request.user
    mark.save()
    audit(request.user, "mark_saved", f"{student.reg_no} {unit.code} cat={cat} exam={exam} -> {mark.status}")
    return Response(services.mark_payload(student, unit, mark))


@api_view(["POST"])
@permission_classes([CanEnterMarks])
def raise_exception(request):
    """Ask the HOD/staff to accept a missing mark for a valid reason."""
    unit = services.units_visible_to(request.user).filter(pk=request.data.get("unit_id")).first()
    student = Student.objects.filter(pk=request.data.get("student_id"), program__university=request.user.university).first()
    reason = (request.data.get("reason") or "").strip()
    if not unit or not student:
        return bad("Unit or student not found.", http.HTTP_404_NOT_FOUND)
    if len(reason) < 10:
        return bad("State the reason (deferral, medical, special consideration) in at least 10 characters.")
    year = services.current_year()
    if not Registration.objects.filter(student=student, unit=unit, academic_year=year).exists():
        return bad("The student is not registered for this unit.")
    mark, _ = Mark.objects.get_or_create(student=student, unit=unit, academic_year=year)
    if mark.status == rules.COMPLETE:
        return bad("This mark is already complete; no exception is needed.")
    if mark.on_score_sheet:
        audit(request.user, "exception_refused", f"{student.reg_no} {unit.code}: value exists on score sheet")
        return bad(
            "The mark is on the score sheet. Capture it instead; a reason cannot excuse data that exists.",
            http.HTTP_422_UNPROCESSABLE_ENTITY, code="ON_SCORE_SHEET",
        )
    if mark.requests.filter(kind=CaseRequest.Kind.MISSING_MARK, status=CaseRequest.Status.REQUESTED).exists():
        return bad("There is already an open request for this mark.", http.HTTP_409_CONFLICT)
    req = CaseRequest.objects.create(
        university=request.user.university, kind=CaseRequest.Kind.MISSING_MARK, mark=mark, student=student,
        unit=unit, reason=reason, requested_by=request.user,
    )
    audit(request.user, "exception_requested", f"{student.reg_no} {unit.code}: {reason[:120]}")
    return Response(case_payload(req), status=http.HTTP_201_CREATED)


# ==========================================================================
# HOD
# ==========================================================================
@api_view(["GET"])
@permission_classes([IsHod])
def hod_dashboard(request):
    students = list(services.students_in_scope(request.user))
    at_risk, blocked_total, pending_total = [], 0, 0
    for s in students:
        state = services.student_state(s)
        reasons = []
        if state["gpa"] is not None and state["gpa"] < 2.0:
            reasons.append(f"GPA {state['gpa']}")
        if state["failed"]:
            reasons.append("Failed " + ", ".join(sorted(state["failed"])))
        if float(s.fees_balance) > 0:
            reasons.append(f"Fees KES {float(s.fees_balance):,.0f}")
        blocked_total += sum(1 for v in state["statuses"].values() if v == rules.BLOCKED)
        pending_total += sum(1 for v in state["statuses"].values() if v == rules.PENDING)
        if reasons:
            at_risk.append({"id": s.id, "reg_no": s.reg_no, "name": services.full_name(s.user), "year": s.year, "reasons": reasons})
    open_cases = CaseRequest.objects.filter(
        university=request.user.university, status=CaseRequest.Status.REQUESTED
    )
    if request.user.department:
        open_cases = open_cases.filter(student__program__department=request.user.department)
    return Response({
        "department": request.user.department,
        "students": len(students),
        "at_risk": at_risk,
        "open_cases": open_cases.count(),
        "blocked_marks": blocked_total,
        "pending_marks": pending_total,
    })


@api_view(["GET"])
@permission_classes([IsHod])
def hod_curriculum(request):
    qs = Unit.objects.filter(university=request.user.university).select_related("program", "lecturer")
    if request.user.department:
        qs = qs.filter(program__department=request.user.department)
    return Response([
        {"id": u.id, "code": u.code, "title": u.title, "credits": u.credits, "year": u.year, "semester": u.semester,
         "is_core": u.is_core, "program": u.program.name,
         "lecturer": services.full_name(u.lecturer) if u.lecturer else None,
         "prerequisites": list(u.prerequisites.values_list("code", flat=True))}
        for u in qs
    ])


# ==========================================================================
# Staff (ICT / registry)
# ==========================================================================
@api_view(["GET"])
@permission_classes([IsStaff])
def staff_validation(request):
    """Everything blocking a transcript, grouped per unit, so staff can clear it."""
    out = []
    for u in Unit.objects.filter(university=request.user.university).select_related("lecturer"):
        rows = [r for r in services.roster(u) if r["status"] != rules.COMPLETE]
        if rows:
            out.append({
                "unit": {"id": u.id, "code": u.code, "title": u.title},
                "lecturer": services.full_name(u.lecturer) if u.lecturer else None,
                "rows": rows,
            })
    return Response(out)


@api_view(["GET"])
@permission_classes([IsStaff])
def staff_students(request):
    out = []
    for s in services.students_in_scope(request.user):
        state = services.student_state(s)
        out.append({
            "id": s.id, "reg_no": s.reg_no, "name": services.full_name(s.user), "program": s.program.name,
            "year": s.year, "gpa": state["gpa"], "credits": state["credits"], "fees_balance": float(s.fees_balance),
            "transcript_ready": rules.transcript_readiness(state["statuses"])["ready"],
        })
    return Response(out)


def _transcript(student):
    state = services.student_state(student)
    rows = []
    for m in student.marks.select_related("unit").order_by("academic_year", "unit__code"):
        row = services.mark_payload(student, m.unit, m)
        row["academic_year"] = m.academic_year
        row["credits"] = m.unit.credits
        rows.append(row)
    return {
        "student": {"id": student.id, "reg_no": student.reg_no, "name": services.full_name(student.user), "program": student.program.name},
        "rows": rows, "gpa": state["gpa"], "credits": state["credits"],
        "readiness": rules.transcript_readiness(state["statuses"]),
    }


@api_view(["GET"])
@permission_classes([IsStaff])
def staff_transcript(request, pk):
    s = services.students_in_scope(request.user).filter(pk=pk).first()
    if not s:
        return bad("Student not found.", http.HTTP_404_NOT_FOUND)
    return Response(_transcript(s))


@api_view(["POST"])
@permission_classes([IsStaff])
def staff_transcript_release(request, pk):
    s = services.students_in_scope(request.user).filter(pk=pk).first()
    if not s:
        return bad("Student not found.", http.HTTP_404_NOT_FOUND)
    t = _transcript(s)
    if not t["readiness"]["ready"]:
        audit(request.user, "transcript_blocked", f"{s.reg_no}: " + ",".join(t["readiness"]["blocked_units"]))
        return bad(
            "Transcript cannot be released: marks are missing for " + ", ".join(t["readiness"]["blocked_units"]) + ".",
            http.HTTP_422_UNPROCESSABLE_ENTITY, readiness=t["readiness"],
        )
    audit(request.user, "transcript_released", f"{s.reg_no} transcript released (pending: {','.join(t['readiness']['pending_units']) or 'none'})")
    return Response({"released": True, **t})


@api_view(["GET"])
@permission_classes([IsStaff])
def staff_graduation(request):
    out = []
    for s in services.students_in_scope(request.user):
        g = services.graduation_for(s)
        out.append({"id": s.id, "reg_no": s.reg_no, "name": services.full_name(s.user), "year": s.year, **g})
    out.sort(key=lambda r: (not r["eligible"], r["reg_no"]))
    return Response(out)


@api_view(["PUT"])
@permission_classes([IsStaff])
def staff_set_fees(request, pk):
    s = services.students_in_scope(request.user).filter(pk=pk).first()
    if not s:
        return bad("Student not found.", http.HTTP_404_NOT_FOUND)
    try:
        balance = number(request.data.get("fees_balance"), "Fee balance")
    except ValueError as exc:
        return bad(str(exc))
    if balance is None or balance < 0:
        return bad("Enter the outstanding balance (0 if cleared).")
    old = float(s.fees_balance)
    s.fees_balance = balance
    s.save(update_fields=["fees_balance"])
    audit(request.user, "fees_updated", f"{s.reg_no}: KES {old:,.0f} -> {balance:,.0f}")
    return Response({"id": s.id, "fees_balance": balance})


@api_view(["GET"])
@permission_classes([IsStaff])
def staff_users(request):
    qs = User.objects.filter(university=request.user.university).order_by("role", "username")
    return Response([{**services.user_payload(u), "is_active": u.is_active} for u in qs])


@api_view(["PATCH"])
@permission_classes([IsStaff])
def staff_user_update(request, pk):
    u = User.objects.filter(pk=pk, university=request.user.university).first()
    if not u:
        return bad("User not found.", http.HTTP_404_NOT_FOUND)
    if u.id == request.user.id:
        return bad("You cannot change your own role or access.", http.HTTP_403_FORBIDDEN)
    changes = []
    role = request.data.get("role")
    if role is not None:
        if role not in User.Role.values:
            return bad("Unknown role.")
        if role == "student" and not hasattr(u, "student"):
            return bad("This account has no student record, so it cannot become a student.")
        changes.append(f"role {u.role}->{role}")
        u.role = role
    if "is_active" in request.data:
        active = bool(request.data["is_active"])
        changes.append(f"active {u.is_active}->{active}")
        u.is_active = active
    u.save()
    audit(request.user, "user_updated", f"{u.username}: " + ", ".join(changes))
    return Response({**services.user_payload(u), "is_active": u.is_active})
