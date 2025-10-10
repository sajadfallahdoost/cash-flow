from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = ("phone_number", "email", "role", "is_staff", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("phone_number", "email", "first_name", "last_name", "national_id")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email", "national_id", "avatar_url")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "password1", "password2", "role", "is_staff", "is_superuser", "is_active"),
        }),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")
