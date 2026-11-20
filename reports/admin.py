from django.contrib import admin
from .models import BillingPeriod


class BillingPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'billing_year', 'billing_month', 'payment_method'
                    )


admin.site.register(BillingPeriod, BillingPeriodAdmin)
