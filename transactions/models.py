from django.db import models
from commons.models import TimeStampedModel
from commons.choices import TransactionType
from core.models import Company, Project
from milestones.models import Milestone
from imports.models import SpreadsheetImport

class Category(TimeStampedModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    name = models.CharField(max_length=255)
    t_type = models.CharField(max_length=10, choices=TransactionType.choices)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "categories"
        ordering = ['sort_order', 'name']
        verbose_name = "Category"
        verbose_name_plural = "Categories"

class Transaction(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    milestone = models.ForeignKey(Milestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    import_ref = models.ForeignKey(SpreadsheetImport, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    txn_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.amount} {self.currency} on {self.txn_date}"

    class Meta:
        db_table = "transactions"
        ordering = ['-txn_date']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=['company', 'txn_date']),
            models.Index(fields=['project', 'txn_date']),
        ]
