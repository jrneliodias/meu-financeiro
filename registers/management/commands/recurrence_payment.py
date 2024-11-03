import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from registers.models import RecurringExpense, Expense


class Command(BaseCommand):
    help = 'Create monthly expenses from RecurringExpense'

    def handle(self, *args, **kwargs):
        # Get today's date
        today = now().date().replace(day=1)
        today_month = today.month

        # Get all recurring expenses that need to be added for this month or previous months
        recurring_expenses = RecurringExpense.objects.all()
        print(
            f"Number of recurring expenses to process: {recurring_expenses.count()}")

        for recurring_expense in recurring_expenses:
            # Set the day and month from the recurring expense's start_date, and use the current year
            print(
                f"Processing recurring expense: {recurring_expense.description}")

            expense_date = today.replace(
                month=today_month, day=recurring_expense.start_date.day)

            print(f"Expense date set to: {expense_date}")

            # Check if an expense for this recurring expense already exists for this month
            last_expense = Expense.objects.filter(
                reccurring_expense=recurring_expense,
                date__year=today.year,
                date__month=today_month,
                date__day=expense_date.day
            ).first()

            if last_expense:
                self.stdout.write(
                    f"Expense already exists for {recurring_expense.description} on {expense_date}")

            else:
                # Create a new expense for the same day and month as the start_date of recurring_expense, but with the current year
                Expense.objects.create(
                    user=recurring_expense.user,
                    description=recurring_expense.description,
                    amount=recurring_expense.total_amount,
                    date=expense_date,  # Use the day and month from start_date, and the current year
                    category=recurring_expense.category,
                    payment_method=recurring_expense.payment_method,
                    reccurring_expense=recurring_expense
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Created expense for {recurring_expense.description} on {expense_date}"))

        self.stdout.write(self.style.SUCCESS(
            'Monthly expenses have been created.'))
