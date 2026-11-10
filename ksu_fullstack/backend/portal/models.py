from django.contrib.auth.models import AbstractUser
from django.db import models

from . import rules


class University(models.Model):
    """Tenant. Every other table hangs off this so many universities can share one deployment."""

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        verbose_name_plural = "universities"

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        LECTURER = "lecturer", "Lecturer"
        HOD = "hod", "Head of Department"
        STAFF = "staff", "ICT / Registry staff"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    university = models.ForeignKey(University, null=True, blank=True, on_delete=models.PROTECT)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class Program(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    required_credits = models.PositiveIntegerField(default=120)

    class Meta:
        unique_together = ("university", "code")

    def __str__(self):
        return f"{self.code} {self.name}"


class Unit(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="units")
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=150)
    credits = models.PositiveIntegerField(default=3)
    year = models.PositiveSmallIntegerField(default=1)
    semester = models.PositiveSmallIntegerField(default=1)
    is_core = models.BooleanField(default=True)
    lecturer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="taught_units"
    )
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="unlocks")

    class Meta:
        unique_together = ("university", "code")
        ordering = ["year", "semester", "code"]

    def __str__(self):
        return f"{self.code} {self.title}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    reg_no = models.CharField(max_length=30, unique=True)
    program = models.ForeignKey(Program, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField(default=1)
    semester = models.PositiveSmallIntegerField(default=1)
    fees_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Required before registration can be submitted (see rules.check_profile).
    next_of_kin_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.reg_no} {self.user.get_full_name()}"


class Registration(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="registrations")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    academic_year = models.CharField(max_length=9, default="2026/2027")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "unit", "academic_year")


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="marks")
    academic_year = models.CharField(max_length=9, default="2026/2027")
    cat = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exam = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # True when the lecturer confirms the value exists on the physical/score sheet
    # but has not been typed in. The gate refuses to treat this as "unavailable".
    on_score_sheet = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default=rules.BLOCKED)
    status_note = models.CharField(max_length=300, blank=True)
    entered_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "unit", "academic_year")

    def exception_approved(self):
        return self.requests.filter(kind=CaseRequest.Kind.MISSING_MARK, status=CaseRequest.Status.APPROVED).exists()

    def recompute(self):
        cat = None if self.cat is None else float(self.cat)
        exam = None if self.exam is None else float(self.exam)
        self.status, self.status_note = rules.mark_status(
            cat, exam, self.on_score_sheet, self.exception_approved() if self.pk else False
        )
        return self.status

    def save(self, *args, **kwargs):
        self.recompute()
        super().save(*args, **kwargs)


class CaseRequest(models.Model):
    """A request that needs a human decision: missing-mark reason or prerequisite waiver.

    Anyone allowed to raise one (lecturer, student) can; only HOD/staff can decide."""

    class Kind(models.TextChoices):
        MISSING_MARK = "missing_mark", "Missing mark reason"
        PREREQ_WAIVER = "prereq_waiver", "Prerequisite waiver"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    university = models.ForeignKey(University, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    mark = models.ForeignKey(Mark, null=True, blank=True, on_delete=models.CASCADE, related_name="requests")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="requests")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="requests_made")
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="requests_decided")
    decision_note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """Append-only: every gate decision and human decision is recorded."""

    university = models.ForeignKey(University, null=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    detail = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("Audit entries cannot be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit entries cannot be deleted.")


def audit(user, action, detail):
    AuditLog.objects.create(
        university=getattr(user, "university", None), actor=user, action=action, detail=detail[:400]
    )
