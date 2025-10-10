from django.contrib import admin
from .models import Holding, Company, Project

@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "base_currency", "holding", "created_at")
    list_filter = ("base_currency",)
    search_fields = ("name", "holding__name")
    ordering = ("name",)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "status", "start_date", "end_date")
    list_filter = ("status", "company")
    search_fields = ("code", "name", "company__name")
    ordering = ("-start_date",)
