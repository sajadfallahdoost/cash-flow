from django.db import models
from django.contrib.postgres.fields import JSONField  # For older Django versions use this line
# from django.db.models import JSONField  # For Django 3.1+ use this line
from accounts.models import User
from commons.choices import AuditAction
from commons.models import TimeStampedModel

class AuditLog(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    entity_type = models.CharField(max_length=100)  # e.g. "Transaction"
    entity_id = models.IntegerField()
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    diff = models.JSONField()  # structured before/after data

    def __str__(self):
        return f"[{self.created_at.date()}] {self.user} {self.action} {self.entity_type}#{self.entity_id}"

    class Meta:
        db_table = "audit_logs"
        ordering = ['-created_at']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'created_at']),
        ]
