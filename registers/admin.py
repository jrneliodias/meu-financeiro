from django.contrib import admin
# Register your models here.
from .models import Expense, Income, Investment, Category, PaymentMethod


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'date',
                    'category', 'payment_method',  'amount')
    # Filtros por categoria e método de pagamento
    list_filter = ('date', 'category', 'payment_method')
    search_fields = ('description',)  # Habilitar pesquisa pela descrição
    list_per_page = 30


admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income)
admin.site.register(Investment)
admin.site.register(Category)
admin.site.register(PaymentMethod)
