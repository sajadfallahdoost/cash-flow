# milestones/models.py

from django.db import models
from commons.models import TimeStampedModel
from commons.choices import MilestoneStatus
from core.models import Project

class Milestone(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=255)  # e.g. "دهه دوم اسفند ۱۴۰۳"
    description = models.TextField(blank=True)
    due_date = models.DateField()
    planned_amt = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=MilestoneStatus.choices, default=MilestoneStatus.PLANNED)
    slice_start = models.DateField(null=True, blank=True)
    slice_end = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "milestones"
        ordering = ['due_date']
        indexes = [
            models.Index(fields=["project", "due_date"]),
        ]
