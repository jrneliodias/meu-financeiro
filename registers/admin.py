from django.contrib import admin
from .models import *
from rangefilter.filters import DateRangeFilter


@admin.action(description="Duplicate selected entries")
def duplicate_entries(modeladmin, request, queryset):
    for obj in queryset:
        obj.pk = None
        obj.save()


@admin.action(description="Triplicate selected entries")
def triplicate_entries(modeladmin, request, queryset):
    for obj in queryset:
        for _ in range(3):
            obj.pk = None
            obj.save()



class ExpenseAdmin(admin.ModelAdmin):
    ordering = ['-date']
    list_display = ('description', 'date',
                    'category', 'payment_method',  'amount', 'reccurring_expense', 'updated_at')
    list_filter = (('date', DateRangeFilter),
                   'payment_method', 'category', 'reccurring_expense')
    search_fields = ('description',)
    list_per_page = 40
    actions = [duplicate_entries, triplicate_entries]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category', 'payment_method', 'reccurring_expense', 'installment_plan'
        )


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'created_at', 'updated_at')
    list_filter = ('type',)
    search_fields = ('name',)
    ordering = ['name']


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0
    fields = ['description', 'amount', 'date', 'category',
              'payment_method']
    readonly_fields = ['description', 'amount', 'date', 'category',
                       'payment_method']


class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'total_amount', 'total_installments',
                    'start_date', 'category', 'payment_method', 'created_at', 'updated_at')
    search_fields = ('description',)
    inlines = [ExpenseInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category', 'payment_method'
        )


class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'total_amount', 'start_date',
                    'category', 'payment_method', 'generate_debit', 'is_international', 'created_at', 'updated_at')
    search_fields = ('description',)
    ordering = ['-generate_debit']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category', 'payment_method'
        )

    inlines = [ExpenseInline]


class IncomeAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount',
                    'date', 'category', 'created_at', 'updated_at')
    search_fields = ('description',)
    ordering = ['-date']
    list_filter = (('date', DateRangeFilter), 'category')
    actions = [duplicate_entries]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category'
        )


class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_billing_day', 'created_at', 'updated_at')
    search_fields = ('name',)


class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount',
                    'date', 'created_at', 'updated_at')
    search_fields = ('description',)
    ordering = ['-date']
    actions = [duplicate_entries]


class QuickFillPresetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'description', 'default_amount', 'category',
        'payment_method', 'icon', 'is_active', 'display_order',
        'created_at', 'updated_at',
    )
    list_filter = ('is_active', 'category', 'payment_method')
    search_fields = ('name', 'description')
    ordering = ['display_order', 'name']
    list_editable = ('is_active', 'display_order')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category', 'payment_method'
        )


admin.site.register(Category, CategoryAdmin)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Income, IncomeAdmin)
admin.site.register(Investment, InvestmentAdmin)
admin.site.register(PaymentMethod, PaymentMethodAdmin)
admin.site.register(Installment, InstallmentAdmin)
admin.site.register(RecurringExpense, RecurringExpenseAdmin)
admin.site.register(QuickFillPreset, QuickFillPresetAdmin)


@admin.register(CategoryBudgetEstimate)
class CategoryBudgetEstimateAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'month', 'year']
    list_filter = ['year', 'month', 'category']
    search_fields = ['user__username', 'category__name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'category')
