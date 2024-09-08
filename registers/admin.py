from django.contrib import admin
# Register your models here.
from .models import Expense, Income, Investment, Category, PaymentMethod, Installment


class ExpenseAdmin(admin.ModelAdmin):
    ordering = ['-date']  # Default order by date descending
    list_display = ('description', 'date',
                    'category', 'payment_method',  'amount', 'created_at')
    # Filtros por categoria e método de pagamento
    list_filter = ('date', 'category', 'payment_method')
    search_fields = ('description',)  # Habilitar pesquisa pela descrição
    list_per_page = 30


admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income)
admin.site.register(Investment)
admin.site.register(Category)
admin.site.register(PaymentMethod)
admin.site.register(Installment)
