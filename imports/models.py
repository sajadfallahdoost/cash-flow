from django.db import models
from commons.models import TimeStampedModel
from commons.choices import ImportStatus
from core.models import Project
from accounts.models import User  # assuming your user model is in `accounts`

class SpreadsheetImport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='imports')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_imports')
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.status}"

    class Meta:
        db_table = "spreadsheet_imports"
        ordering = ['-uploaded_at']
        verbose_name = "Spreadsheet Import"
        verbose_name_plural = "Spreadsheet Imports"

class ImportError(TimeStampedModel):
    import_ref = models.ForeignKey(SpreadsheetImport, on_delete=models.CASCADE, related_name='errors')
    row_number = models.IntegerField()
    column_name = models.CharField(max_length=100)
    error_msg = models.TextField()

    def __str__(self):
        return f"Row {self.row_number}, Col {self.column_name}: {self.error_msg[:50]}..."

    class Meta:
        db_table = "import_errors"
        ordering = ['import_ref', 'row_number']
        verbose_name = "Import Error"
        verbose_name_plural = "Import Errors"
