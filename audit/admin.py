from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "entity_type", "entity_id", "action", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_type", "user__email")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("diff",)
