from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views.generic import UpdateView

from registers.forms import ExpenseForm
from registers.models import Expense
from utils.http import safe_return_url


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    form_class = ExpenseForm
    template_name = 'register/expense_form.html'
    success_url = '/'

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(next_url=safe_return_url(self.request, 'next'), **kwargs)

    def get_success_url(self):
        return safe_return_url(self.request, 'next') or super().get_success_url()

    def form_valid(self, form):
        messages.success(self.request, _("Expense updated successfully."))
        return super().form_valid(form)
