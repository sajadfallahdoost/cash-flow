# milestones/admin.py

from django.contrib import admin
from .models import Milestone

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "status", "due_date", "planned_amt")
    list_filter = ("status", "project")
    search_fields = ("name", "project__name")
    ordering = ("due_date",)
