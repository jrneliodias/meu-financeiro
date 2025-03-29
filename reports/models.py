from django.db import models

from registers.models import PaymentMethod

# Create your models here.


class BillingPeriod(models.Model):
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    billing_month = models.CharField(max_length=20)  # e.g., "January"
    billing_year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['payment_method', 'billing_month', 'billing_year']
        ordering = ['billing_year', 'start_date']

    def __str__(self):
        return f"{self.payment_method} - {self.billing_month} {self.billing_year}"
