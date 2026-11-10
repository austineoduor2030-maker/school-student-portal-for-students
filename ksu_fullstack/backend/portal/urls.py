from django.urls import path

from . import views as v

urlpatterns = [
    # auth
    path("auth/login/", v.login),
    path("auth/logout/", v.logout),
    path("me/", v.me),
    # student
    path("student/dashboard/", v.student_dashboard),
    path("student/units/", v.student_units),
    path("student/registrations/", v.student_register),
    path("student/registrations/<int:pk>/", v.student_unregister),
    path("student/results/", v.student_results),
    path("student/graduation/", v.student_graduation),
    path("student/fees/", v.student_fees),
    path("student/profile/", v.student_profile),
    path("student/requests/", v.student_requests),
    path("student/ask/", v.student_ask),
    # marks (lecturer + staff)
    path("marks/units/", v.mark_units),
    path("marks/units/<int:pk>/roster/", v.unit_roster),
    path("marks/", v.save_mark),
    path("marks/exceptions/", v.raise_exception),
    # HOD / staff decisions
    path("cases/", v.cases),
    path("cases/<int:pk>/decide/", v.case_decide),
    path("audit/", v.audit_log),
    # HOD
    path("hod/dashboard/", v.hod_dashboard),
    path("hod/curriculum/", v.hod_curriculum),
    # staff
    path("staff/validation/", v.staff_validation),
    path("staff/students/", v.staff_students),
    path("staff/students/<int:pk>/transcript/", v.staff_transcript),
    path("staff/students/<int:pk>/transcript/release/", v.staff_transcript_release),
    path("staff/students/<int:pk>/fees/", v.staff_set_fees),
    path("staff/graduation/", v.staff_graduation),
    path("staff/users/", v.staff_users),
    path("staff/users/<int:pk>/", v.staff_user_update),
]
