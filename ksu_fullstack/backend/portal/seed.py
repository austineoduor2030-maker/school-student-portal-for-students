"""Demo data. DEMO ONLY: fake people, one shared throwaway password."""
from .models import Mark, Program, Registration, Student, Unit, University, User, CaseRequest

# (code, title, year, semester, core, prerequisites)
UNITS = [
    ("CIT 101", "Introduction to programming", 1, 1, True, []),
    ("CIT 110", "Discrete mathematics", 1, 1, True, []),
    ("CIT 120", "Computer systems", 1, 1, True, []),
    ("CIT 102", "Object-oriented programming", 1, 2, True, ["CIT 101"]),
    ("CIT 201", "Databases I", 1, 2, True, ["CIT 101"]),
    ("CIT 220", "Data structures", 2, 1, True, ["CIT 102"]),
    ("CIT 305", "Databases II", 2, 1, True, ["CIT 201"]),
    ("CIT 240", "Web development", 2, 1, True, ["CIT 101"]),
    ("CIT 260", "Operating systems", 2, 1, True, ["CIT 120"]),
    ("CIT 250", "Software engineering", 2, 2, True, ["CIT 102"]),
    ("CIT 310", "Final year project", 3, 1, True, ["CIT 250"]),
    ("CIT 330", "Elective: applied AI", 3, 2, False, []),
]


def _user(username, first, last, role, uni, dept, password):
    u, _ = User.objects.get_or_create(username=username, defaults=dict(first_name=first, last_name=last, role=role, university=uni, department=dept))
    u.first_name, u.last_name, u.role, u.university, u.department = first, last, role, uni, dept
    u.set_password(password)
    u.save()
    return u


def _student(username, first, last, reg, program, year, sem, fees, phone, uni, password):
    u = _user(username, first, last, "student", uni, program.department, password)
    s, _ = Student.objects.update_or_create(
        user=u, defaults=dict(reg_no=reg, program=program, year=year, semester=sem, fees_balance=fees, next_of_kin_phone=phone)
    )
    return s


def _mark(student, unit, cat, exam, sheet=False, by=None):
    m, _ = Mark.objects.get_or_create(student=student, unit=unit, academic_year="2025/2026")  # last year's results
    m.cat, m.exam, m.on_score_sheet, m.entered_by = cat, exam, sheet, by
    m.save()
    return m


def build_demo(password="demo12345"):
    uni, _ = University.objects.get_or_create(code="KSU", defaults={"name": "Kisii University"})
    # required_credits is 36 here only so the demo can reach "graduation eligible".
    prog, _ = Program.objects.get_or_create(
        university=uni, code="CIT", defaults=dict(name="BSc Computer Science", department="Computer Science", required_credits=36)
    )
    lec1 = _user("lec1", "James", "Otieno", "lecturer", uni, "Computer Science", password)
    lec2 = _user("lec2", "Grace", "Kemunto", "lecturer", uni, "Computer Science", password)
    hod = _user("hod1", "Peter", "Ochieng", "hod", uni, "Computer Science", password)
    staff = _user("staff1", "Mary", "Wanjiru", "staff", uni, "ICT", password)

    units = {}
    for code, title, y, s, core, _pre in UNITS:
        units[code], _ = Unit.objects.update_or_create(
            university=uni, code=code, defaults=dict(program=prog, title=title, year=y, semester=s, is_core=core, credits=3)
        )
    for code, *_rest, pre in UNITS:
        units[code].prerequisites.set([units[p] for p in pre])
    for code in ("CIT 220", "CIT 240", "CIT 305", "CIT 101", "CIT 102"):
        units[code].lecturer = lec1
        units[code].save()
    for code in ("CIT 260", "CIT 201", "CIT 110", "CIT 120", "CIT 250"):
        units[code].lecturer = lec2
        units[code].save()

    # Brian: failed CIT 201, so CIT 305 is blocked. No next of kin phone, so registering is blocked until added.
    brian = _student("brian", "Brian", "Mokaya", "CIT/0001/2024", prog, 2, 1, 0, "", uni, password)
    for code in ("CIT 101", "CIT 110", "CIT 120", "CIT 102"):
        _mark(brian, units[code], 22, 55)
    _mark(brian, units["CIT 201"], 10, 20)  # 30 total = fail

    # Amina: fee balance holds registration; one current mark not yet captured.
    amina = _student("amina", "Amina", "Hassan", "CIT/0002/2024", prog, 2, 1, 15000, "0712345678", uni, password)
    for code in ("CIT 101", "CIT 110", "CIT 120", "CIT 102", "CIT 201"):
        _mark(amina, units[code], 20, 50)
    Registration.objects.get_or_create(student=amina, unit=units["CIT 220"], academic_year="2026/2027")

    # Peter: the three marks-gate cases in one place.
    peter = _student("peter", "Peter", "Nyamweya", "CIT/0003/2024", prog, 2, 1, 0, "0798765432", uni, password)
    for code in ("CIT 101", "CIT 110", "CIT 120", "CIT 102", "CIT 201"):
        _mark(peter, units[code], 25, 55)
    for code in ("CIT 220", "CIT 240", "CIT 260"):
        Registration.objects.get_or_create(student=peter, unit=units[code], academic_year="2026/2027")
    Mark.objects.update_or_create(student=peter, unit=units["CIT 220"], academic_year="2026/2027", defaults=dict(cat=24, exam=48, entered_by=lec1))
    # CIT 240: exam missing, reason approved -> pending
    m240, _ = Mark.objects.get_or_create(student=peter, unit=units["CIT 240"], academic_year="2026/2027")
    m240.cat, m240.exam, m240.entered_by = 20, None, lec1
    m240.save()
    CaseRequest.objects.get_or_create(
        university=uni, kind="missing_mark", mark=m240, student=peter, unit=units["CIT 240"],
        defaults=dict(reason="Medical: hospitalised during the exam, deferral approved.", requested_by=lec1, status="approved", decided_by=hod),
    )
    m240.save()
    # CIT 260: exam is on the score sheet but not captured -> blocked even though a reason could be given
    m260, _ = Mark.objects.get_or_create(student=peter, unit=units["CIT 260"], academic_year="2026/2027")
    m260.cat, m260.exam, m260.on_score_sheet, m260.entered_by = 18, None, True, lec2
    m260.save()

    return dict(uni=uni, prog=prog, units=units, lec1=lec1, lec2=lec2, hod=hod, staff=staff, brian=brian, amina=amina, peter=peter)
