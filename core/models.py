from django.db import models
from commons.models import TimeStampedModel

class Holding(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "holdings"
        ordering = ['name']
        verbose_name = "Holding"
        verbose_name_plural = "Holdings"

class Company(TimeStampedModel):
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=255)
    base_currency = models.CharField(max_length=3)

    def __str__(self):
        return f"{self.name} ({self.base_currency})"

    class Meta:
        db_table = "companies"
        ordering = ['name']
        verbose_name = "Company"
        verbose_name_plural = "Companies"

class Project(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="projects")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        db_table = "projects"
        ordering = ['-start_date']
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        indexes = [
            models.Index(fields=['company', 'start_date']),
        ]
