from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.generic import UpdateView
from registers.forms import ExpenseForm
from registers.models import Expense


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'reports/expense_update.html'
    success_url = '/'

    def get_form_kwargs(self):
        """Inject user into form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        """Remove installments field for edit form."""
        form = super().get_form(form_class)
        # installments field is only for creation, not editing
        if 'installments' in form.fields:
            del form.fields['installments']
        return form

    def _next_url(self):
        candidate = self.request.POST.get('next') or self.request.GET.get('next')
        if candidate and url_has_allowed_host_and_scheme(
                candidate, allowed_hosts={self.request.get_host()}):
            return candidate
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self._next_url()
        return context

    def get_success_url(self):
        return self._next_url() or super().get_success_url()

    def form_valid(self, form):
        """Save and add success message."""
        messages.success(self.request, _("Expense updated successfully."))
        return super().form_valid(form)
