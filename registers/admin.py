from django.contrib import admin
# Register your models here.
from .models import Expense, Income, Investment, Category, PaymentMethod


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date',
                    'category', 'payment_method')
    # Filtros por categoria e método de pagamento
    list_filter = ('category', 'payment_method', 'date')
    search_fields = ('description',)  # Habilitar pesquisa pela descrição
    ist_per_page = 20  # Exibir 20 despesas por página


admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income)
admin.site.register(Investment)
admin.site.register(Category)
admin.site.register(PaymentMethod)
