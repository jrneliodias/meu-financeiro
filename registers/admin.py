from django.contrib import admin
# Register your models here.
from .models import *


class ExpenseAdmin(admin.ModelAdmin):
    ordering = ['-date']  # Default order by date descending
    list_display = ('description', 'date',
                    'category', 'payment_method',  'amount', 'created_at')
    # Filtros por categoria e método de pagamento
    list_filter = ('date', 'category', 'payment_method')
    search_fields = ('description',)  # Habilitar pesquisa pela descrição
    list_per_page = 40


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


admin.site.register(Category, CategoryAdmin)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income)
admin.site.register(Investment)
admin.site.register(PaymentMethod)
admin.site.register(Installment, InstallmentAdmin)
admin.site.register(RecurringExpense, RecurringExpenseAdmin)
