from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

# (url name, Font Awesome icon, label, url-name prefixes that mark the item active)
SIDEBAR_ITEMS = [
    ('expense_report', 'fa-house', _('Dashboard'),
     ('expense_report', 'dashboard_', 'budget_breakdown', 'expense_list_page', 'expense_update')),
    ('register_expense', 'fa-coins', _('Register Expense'), ('register_expense',)),
    ('register_income', 'fa-coins', _('Register Income'), ('register_income',)),
    ('quick_fill_preset_list', 'fa-bolt', _('Quick Fill Presets'), ('quick_fill_preset_',)),
    ('recurring_expense_list', 'fa-repeat', _('Recurring Expenses'),
     ('recurring_expense_', 'register_recurring_expense')),
    ('recurring_payments', 'fa-list-check', 'Pagamentos do mês', ('recurring_payments',)),
    ('budget_estimate_list', 'fa-chart-pie', _('Budget Estimates'), ('budget_estimate_',)),
    ('csv_import', 'fa-file-csv', _('CSV Import'), ('csv_',)),
    ('expense_export', 'fa-file-arrow-down', _('Export'), ('expense_export',)),
]


@register.inclusion_tag('core/sidebar_nav.html', takes_context=True)
def sidebar_nav(context):
    match = context['request'].resolver_match
    current = match.url_name if match else ''
    return {'items': [
        {'url_name': url_name, 'icon': icon, 'label': label, 'active': current.startswith(active_prefixes)}
        for url_name, icon, label, active_prefixes in SIDEBAR_ITEMS
    ]}
