from django.db import models


class TransactionType(models.TextChoices):
    INFLOW = "INFLOW", "Inflow"
    OUTFLOW = "OUTFLOW", "Outflow"


class MilestoneStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    ACHIEVED = "ACHIEVED", "Achieved"
    CANCELLED = "CANCELLED", "Cancelled"


class ImportStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    LOGIN  = "LOGIN", "Login"
