from django.db import models
from commons.models import TimeStampedModel

class ExchangeRate(TimeStampedModel):
    base_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    rate_date = models.DateField()

    def __str__(self):
        return f"{self.base_currency} → {self.target_currency} @ {self.rate} on {self.rate_date}"

    class Meta:
        db_table = "exchange_rates"
        ordering = ['-rate_date']
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        constraints = [
            models.UniqueConstraint(
                fields=['base_currency', 'target_currency', 'rate_date'],
                name='unique_rate_per_day'
            )
        ]
        indexes = [
            models.Index(fields=['base_currency', 'target_currency', 'rate_date']),
        ]
