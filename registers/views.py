from django.shortcuts import render, redirect
from .forms import ExpenseForm
from .services import ExpenseService, InstallmentService
from django.contrib import messages
# Create your views here.


def index(request):
    return render(request, 'core/index.html')


def register_expense(request):
    if (request.method == 'POST'):
        form = ExpenseForm(request.POST)
        if not form.is_valid():
            return
        expense_data = form.cleaned_data

        user = request.user

        if expense_data['installments'] > 1:
            installment_service = InstallmentService()
            installment_plan, expenses = installment_service.create_installments(
                user, expense_data)
            messages.success(
                request, f"{expense_data['installments']} installments have been registered.")
        else:
            expense_service = ExpenseService()
            expense = expense_service.create_single_expense(
                user, expense_data)
            messages.success(request, "Expense has been registered.")

        return redirect('expense_success')

    else:
        form = ExpenseForm()
    return render(request, 'register/expense_form.html', {'form': form})


def expense_success(request):
    return render(request, 'register/expense_success.html')
