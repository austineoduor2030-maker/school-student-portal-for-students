from rest_framework.permissions import BasePermission


def role_required(*roles):
    """Build a permission class allowing only the given roles."""

    class _Role(BasePermission):
        message = "Your role cannot do this."

        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.role in roles)

    _Role.__name__ = "Role_" + "_".join(roles)
    return _Role


IsStudent = role_required("student")
IsLecturer = role_required("lecturer")
IsDecider = role_required("hod", "staff")          # may approve exceptions
CanEnterMarks = role_required("lecturer", "staff")
IsHod = role_required("hod")
IsStaff = role_required("staff")
IsHodOrStaff = role_required("hod", "staff")
