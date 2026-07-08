from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra info", {"fields": ("phone_number",)}),
    )
    list_display = ("username", "email", "phone_number", "is_staff", "is_active")
