from django.contrib import admin
from .models import SpreadsheetImport, ImportError

@admin.register(SpreadsheetImport)
class SpreadsheetImportAdmin(admin.ModelAdmin):
    list_display = ("filename", "status", "project", "uploaded_by", "uploaded_at", "processed_at")
    list_filter = ("status", "uploaded_at")
    search_fields = ("filename", "uploaded_by__email")
    ordering = ("-uploaded_at",)

@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ("import_ref", "row_number", "column_name", "created_at")
    search_fields = ("column_name", "error_msg")
    ordering = ("-created_at",)
