from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, CaseRequest, Mark, Program, Registration, Student, Unit, University, User


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Portal", {"fields": ("role", "university", "department")}),)
    list_display = ("username", "get_full_name", "role", "university", "is_active")
    list_filter = ("role", "university", "is_active")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "detail")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register([University, Program, Unit, Student, Registration, Mark, CaseRequest])
