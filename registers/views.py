from django.shortcuts import render, redirect
from .forms import ExpenseForm
# Create your views here.


def index(request):
    return render(request, 'core/index.html')


def register_expense(request):
    if (request.method == 'POST'):
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            return redirect('expense_success')
    else:
        form = ExpenseForm()
    return render(request, 'register/expense_form.html', {'form': form})


def expense_success(request):
    return render(request, 'register/expense_success.html')
