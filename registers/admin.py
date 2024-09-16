from django.contrib import admin
# Register your models here.
from .models import *
from rangefilter.filters import DateRangeFilter
from django.db.models import Sum


@admin.action(description="Duplicate selected entries")
def duplicate_entries(modeladmin, request, queryset):
    for obj in queryset:
        # Create a copy of the object
        obj.pk = None  # Set pk to None to create a new object instead of updating the existing one
        obj.save()     # Save the new duplicated object

   # Register the duplicate action


class ExpenseAdmin(admin.ModelAdmin):
    ordering = ['-date']  # Default order by date descending
    list_display = ('description', 'date',
                    'category', 'payment_method',  'amount', 'created_at')
    # Filtros por categoria e método de pagamento
    list_filter = (('date', DateRangeFilter), 'category', 'payment_method')
    search_fields = ('description',)  # Habilitar pesquisa pela descrição
    list_per_page = 40
    actions = [duplicate_entries]


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'created_at', 'updated_at')
    list_filter = ('type',)
    search_fields = ('name',)
    ordering = ['name']


class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'total_amount', 'total_installments',
                    'start_date', 'category', 'payment_method', 'created_at', 'updated_at')
    search_fields = ('name',)


class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'total_amount', 'start_date',
                    'category', 'payment_method', 'created_at', 'updated_at')
    search_fields = ('name',)


class IncomeAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount',
                    'date', 'category', 'created_at', 'updated_at')
    search_fields = ('description',)
    ordering = ['-date']
    actions = [duplicate_entries]


admin.site.register(Category, CategoryAdmin)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income, IncomeAdmin)
admin.site.register(Investment)
admin.site.register(PaymentMethod)
admin.site.register(Installment, InstallmentAdmin)
admin.site.register(RecurringExpense, RecurringExpenseAdmin)
