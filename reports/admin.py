from django.contrib import admin
from .models import BillingPeriod
# Register your models here.


class BillingPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'billing_year', 'billing_month', 'payment_method'
                    )


admin.site.register(BillingPeriod, BillingPeriodAdmin)
