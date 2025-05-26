from django.shortcuts import render, redirect
from .forms import ExpenseForm, IncomeForm
from .services import ExpenseService, InstallmentService, IncomeService
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Expense

# Create your views here.

installment_service = InstallmentService()
expense_service = ExpenseService()
income_service = IncomeService()


def register_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, 'register/expense_form.html', {'form': form})

        expense_data = form.cleaned_data
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "User isn't logged in")
            # or wherever you want to redirect unauthenticated users

        if expense_data['installments'] > 1:
            installment_service.create_installments(user, expense_data)
            messages.success(
                request, f"{expense_data['installments']} installments have been registered.")
        else:
            expense = expense_service.create_single_expense(user, expense_data)
            messages.success(
                request, f"Expense {expense.__str__()} has been registered.")

        # Redirect after successful POST
        return redirect('register_expense')

    else:
        # Handle quick fill parameter
        quick_fill = request.GET.get('quick_fill')
        form = ExpenseForm(user=request.user)
        if quick_fill:
            form.apply_quick_fill(quick_fill)

    return render(request, 'register/expense_form.html', {'form': form})


def expense_success(request):
    return render(request, 'register/expense_success.html')


def register_income(request):
    if (request.method == 'POST'):
        form = IncomeForm(request.POST)
        if not form.is_valid():
            return render(request, 'register/income_form.html', {'form': form})
        income_data = form.cleaned_data

        user = request.user

        if not user.is_authenticated:
            messages.error(
                request, "user isn't logged in")
            return render(request, 'register/income_form.html', {'form': form})

        income = income_service.create_income(user, income_data)

        return redirect('expense_success')

    else:
        form = IncomeForm()
    return render(request, 'register/income_form.html', {'form': form})


def income_success(request):
    return render(request, 'register/income_success.html')


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'register/expense_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        quick_fill = self.request.GET.get('quick_fill')
        if quick_fill:
            form.apply_quick_fill(quick_fill)
        return form
